"""Run a trusted local range-render adapter against an owner-private Sites queue."""
import argparse, json, os, subprocess, threading, time, urllib.request
from pathlib import Path


def run(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    site = config["site"].rstrip("/")
    if not site.startswith("https://") and not site.startswith("http://127.0.0.1:"):
        raise ValueError("Use HTTPS or a loopback test server")
    state = (config_path.parent / config["state_dir"]).resolve()
    state.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("STUDIO_SITES_TOKEN", "")
    current = [None]
    stopped = threading.Event()

    def request(path="", data=None, method=None, lease=None):
        headers = {"OAI-Sites-Authorization": "Bearer " + token}
        if lease:
            headers["X-Render-Lease"] = lease
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(site + "/api/renders" + path, data=data,
                                     headers=headers, method=method or ("POST" if data is not None else "GET"))
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)

    def heartbeat():
        while not stopped.is_set():
            try:
                job = current[0]
                request("/heartbeat", {"job": job["id"] if job else None})
                if job:
                    request("/" + job["id"] + "/progress", {"lease": job["lease"], "progress": 0})
            except Exception:
                pass
            stopped.wait(10)

    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        while True:
            try:
                jobs = request()["versions"]
                jobs = [j for j in jobs if j["status"] == "queued" or
                        (j["status"] == "running" and time.time()*1000-j.get("updated", 0) > 120000)]
                if not jobs:
                    time.sleep(4)
                    continue
                job = request("/" + min(jobs, key=lambda j: j["created"])["id"] + "/claim", {})
                current[0] = job
                folder = state / job["id"]
                folder.mkdir(exist_ok=True)
                job_path, receipt_path = folder / "job.json", folder / "receipt.json"
                job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
                # Command comes only from the trusted local config, never from the cloud job.
                command = [s.replace("{job}", str(job_path)).replace("{receipt}", str(receipt_path))
                           for s in config["command"]]
                with (folder / "render.log").open("w", encoding="utf-8") as log:
                    subprocess.run(command, cwd=config_path.parent, check=True, stdout=log, stderr=log,
                                   env={k:v for k,v in os.environ.items() if k != "STUDIO_SITES_TOKEN"})
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if sorted(p["index"] for p in receipt["parts"]) != list(range(len(job["ranges"]))):
                    raise ValueError("Adapter must return every requested range exactly once")
                for part in receipt["parts"]:
                    data = Path(part["path"]).read_bytes()
                    count = (len(data)+262143)//262144
                    if not 1 <= count <= 128:
                        raise ValueError("Each clip must be nonempty and at most 32 MiB")
                    for chunk in range(count):
                        request(f'/{job["id"]}/media/{part["index"]}?chunk={chunk}&count={count}',
                                data[chunk*262144:(chunk+1)*262144], "PUT", job["lease"])
                safe = {k: receipt[k] for k in ("renderedFrames", "cachedFrames", "totalFrames")}
                request("/" + job["id"] + "/finish", {"lease": job["lease"], "receipt": safe})
                print("Ready", job["id"], flush=True)
                current[0] = None
            except Exception as error:
                print("Render failed:", type(error).__name__, flush=True)
                if current[0]:
                    try:
                        request("/" + current[0]["id"] + "/fail", {"lease": current[0]["lease"],
                                "error": "렌더 PC의 작업 로그를 확인한 뒤 재시도하세요."})
                    except Exception:
                        pass
                current[0] = None
                time.sleep(15)
    finally:
        stopped.set()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="Trusted local worker configuration JSON")
    run(parser.parse_args().config)
