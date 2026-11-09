"""Loopback-only review application. No repository directory listing."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import sys
import time
from urllib.parse import quote, unquote, urlsplit

from media import edited_cues, format_srt, load_cues, require_caption_export
from model import Conflict, read_json, write_json

UI = Path(__file__).resolve().parent.parent / 'assets'
ROUTE_ID = r'([a-z0-9][a-z0-9-]{0,63})'
HANDOFF_ID = r'([a-f0-9]{32})'


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, project, port):
        self.project = project
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(12)
        super().__init__(('127.0.0.1', port), Handler)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    @property
    def project(self):
        return self.server.project

    def write_headers(self, status, mime, size, extra=()):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-store')
        for key, value in extra:
            self.send_header(key, value)
        self.end_headers()

    def payload(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.write_headers(status, 'application/json; charset=utf-8', len(data))
        if self.command != 'HEAD':
            self.wfile.write(data)

    def good_host(self):
        return self.headers_in('Host') in {f'127.0.0.1:{self.server.server_port}',
                                          f'localhost:{self.server.server_port}'}

    def headers_in(self, name):
        return self.headers.get(name)

    def stream(self, path, mime=None, extra=()):
        mime = mime or mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if mime.startswith(('text/', 'application/javascript', 'application/json')):
            mime += '; charset=utf-8'
        with path.open('rb') as file:
            size = path.stat().st_size
            start, end = 0, size - 1
            raw = self.headers_in('Range')
            code = 200
            more = [('Accept-Ranges', 'bytes'), *extra]
            if raw:
                match = re.fullmatch(r'bytes=(\d{0,18})-(\d{0,18})', raw)
                if match and any(match.groups()):
                    first, last = match.groups()
                    if first:
                        start = int(first)
                        end = min(end, int(last)) if last else end
                    else:
                        start = max(0, size - int(last))
                if not match or not any(match.groups()) or not 0 <= start <= end < size:
                    return self.write_headers(416, mime, 0, [('Content-Range', f'bytes */{size}')])
                code = 206
                more.append(('Content-Range', f'bytes {start}-{end}/{size}'))
            remaining = max(0, end - start + 1)
            self.write_headers(code, mime, remaining, more)
            if self.command == 'HEAD':
                return
            file.seek(start)
            while remaining:
                block = file.read(min(remaining, 256 * 1024))
                if not block:
                    return
                self.wfile.write(block)
                remaining -= len(block)

    def html_preview(self, key, suffix):
        artifact = self.project.artifact(key)
        if artifact['kind'] != 'html':
            raise FileNotFoundError('HTML preview not found')
        file = str(PurePosixPath(artifact['file']).parent / suffix)
        if file not in [artifact['file'], *artifact.get('assets', [])]:
            raise FileNotFoundError('File is outside the registered preview')
        origin = f'http://{self.headers_in("Host")}'
        policy = ('sandbox allow-scripts; default-src \'none\'; '
                  f'script-src \'unsafe-inline\' {origin}; style-src \'unsafe-inline\' {origin}; '
                  f'img-src {origin} data:; media-src {origin}; font-src {origin}; '
                  'base-uri \'none\'; form-action \'none\'; frame-src \'none\'')
        return self.stream(self.project.local(file), extra=[('Content-Security-Policy', policy)])

    def get(self, path):
        if path == '/':
            data = (UI / 'index.html').read_text(encoding='utf-8').replace('__APP_TOKEN__', self.server.token).encode()
            self.write_headers(200, 'text/html; charset=utf-8', len(data), [
                ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; "
                 "img-src 'self' data:; media-src 'self'; frame-src 'self'; object-src 'none'; "
                 "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")])
            if self.command != 'HEAD':
                self.wfile.write(data)
            return
        if path in ('/app.js', '/requests.js', '/versions.js', '/style.css'):
            return self.stream(UI / path[1:])
        if path == '/api/health':
            return self.payload({'instance': self.server.instance})
        if path == '/api/board':
            return self.payload({'project': self.project.root.name, 'artifacts': self.project.artifacts()})
        if path == '/api/requests':
            return self.payload(self.project.requests())
        match = re.fullmatch(rf'/api/versions/{ROUTE_ID}', path)
        if match:
            return self.payload(self.project.versions(match[1]))
        match = re.fullmatch(rf'/versions/{ROUTE_ID}/([1-9][0-9]*)/(video|download)', path)
        if match:
            key, rev, action = match.groups()
            extra = [('Content-Disposition', f'attachment; filename="{key}-rev{rev}.mp4"')] if action == 'download' else []
            return self.stream(self.project.version_video(key, int(rev)), mime='video/mp4', extra=extra)
        match = re.fullmatch(rf'/api/artifacts/{ROUTE_ID}', path)
        if match:
            key = match[1]
            artifact = self.project.artifact(key)
            cues = load_cues(self.project, artifact)
            if artifact['kind'] == 'html':
                artifact['preview'] = f"/preview/{key}/" + quote(PurePosixPath(artifact['file']).name)
            return self.payload({'artifact': artifact, 'cues': cues, 'review': self.project.review(key)})
        match = re.fullmatch(rf'/media/{ROUTE_ID}/(file|music|voice|effects)', path)
        if match:
            key, field = match.groups()
            artifact = self.project.artifact(key)
            if artifact['kind'] not in ('video', 'image') or field not in artifact:
                raise FileNotFoundError('Media not found')
            return self.stream(self.project.asset(artifact, field))
        match = re.fullmatch(rf'/preview/{ROUTE_ID}/(.+)', path)
        if match:
            return self.html_preview(*match.groups())
        match = re.fullmatch(rf'/export/{ROUTE_ID}\.srt', path)
        if match:
            key = match[1]
            cues = load_cues(self.project, self.project.artifact(key))
            review = self.project.review(key)
            require_caption_export(review)
            text = format_srt(edited_cues(cues, review)).encode('utf-8')
            self.write_headers(200, 'application/x-subrip; charset=utf-8', len(text), [
                ('Content-Disposition', f'attachment; filename="{key}.srt"')])
            if self.command != 'HEAD':
                self.wfile.write(text)
            return
        raise FileNotFoundError('Route not found')

    def post(self, path):
        self.close_connection = True
        origin = 'http://' + self.headers_in('Host')
        if (self.headers_in('Origin') != origin or self.headers_in('X-Artifact-Token') != self.server.token
                or self.headers.get_content_type() != 'application/json'):
            return self.payload({'error': 'Use the local Artifact page to save changes'}, 403)
        size = int(self.headers_in('Content-Length') or '0')
        if not 0 < size <= 1_250_000:
            raise ValueError('Invalid request size')
        body = json.loads(self.rfile.read(size))
        if not isinstance(body, dict):
            raise ValueError('Expected a JSON object')
        match = re.fullmatch(rf'/api/requests/{ROUTE_ID}/{ROUTE_ID}', path)
        if match:
            return self.payload(self.project.update_request(match[1], match[2], body))
        match = re.fullmatch(rf'/api/artifacts/{ROUTE_ID}', path)
        if match:
            artifact = self.project.artifact(match[1])
            for field in artifact.get('fingerprints', {}):
                self.project.asset(artifact, field)
            cues = load_cues(self.project, artifact)
            return self.payload(self.project.save_review(match[1], body, len(cues)))
        match = re.fullmatch(rf'/api/artifacts/{ROUTE_ID}/approve-script', path)
        if match:
            artifact = self.project.artifact(match[1])
            original = load_cues(self.project, artifact)
            return self.payload(self.project.approve_script(match[1], body.get('revision'),
                                                            [cue['text'] for cue in original]))
        if path == '/api/handoffs':
            return self.payload(self.project.create_handoff(body), 201)
        match = re.fullmatch(rf'/api/handoffs/{HANDOFF_ID}/ack', path)
        if match:
            return self.payload(self.project.acknowledge(match[1], body.get('by')))
        raise FileNotFoundError('Route not found')

    def dispatch(self, operation):
        try:
            if not self.good_host():
                self.close_connection = True
                return self.payload({'error': 'Loopback host required'}, 403)
            path = unquote(urlsplit(self.path).path, errors='strict')
            operation(path)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except FileNotFoundError:
            self.payload({'error': 'Artifact or route not found'}, 404)
        except Conflict as error:
            self.payload({'error': str(error)}, 409)
        except (ValueError, TypeError, KeyError) as error:
            self.payload({'error': str(error)}, 400)

    def do_GET(self):
        self.dispatch(self.get)

    def do_HEAD(self):
        self.dispatch(self.get)

    def do_POST(self):
        self.dispatch(self.post)


def server_status(project):
    from urllib.request import ProxyHandler, build_opener
    marker = project.storage('runtime', 'server.json')
    if not marker.exists():
        return {'running': False}
    try:
        info = read_json(marker)
        origin = info['url']
        if not re.fullmatch(r'http://127\.0\.0\.1:[1-9]\d{0,4}/', origin):
            raise ValueError('Invalid local server address')
        with build_opener(ProxyHandler({})).open(origin + 'api/health', timeout=0.6) as response:
            current = json.load(response)
        if current['instance'] == info['instance']:
            return dict(info, running=True)
    except (OSError, ValueError, KeyError):
        pass
    return {'running': False}


def serve(project, port):
    running = server_status(project)
    if running['running']:
        print(running['url'], flush=True)
        return
    with project.lock('runtime/server.lock', blocking=False):
        with Server(project, port) as server:
            address = f'http://127.0.0.1:{server.server_port}/'
            marker = project.storage('runtime', 'server.json')
            write_json(marker, {'url': address, 'instance': server.instance, 'pid': os.getpid()})
            print(address, flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                marker.unlink(missing_ok=True)


def open_workspace(project, key=None, port=0):
    """Return a ready local URL, reusing one server per checkout."""
    if key is not None:
        project.artifact(key)
    with project.lock('runtime/launch.lock'):
        running = server_status(project)
        if not running['running']:
            log = project.storage('runtime', 'server.log')
            options = ({'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS}
                       if os.name == 'nt' else {'start_new_session': True})
            with log.open('ab') as output:
                child = subprocess.Popen(
                    [sys.executable, '-u', str(Path(__file__).with_name('artifact.py')),
                     '--project', str(project.root), 'serve', '--port', str(port)],
                    cwd=project.root, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                    close_fds=True, **options)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                running = server_status(project)
                if running['running']:
                    break
                if child.poll() is not None:
                    break
                time.sleep(.1)
            if not running['running']:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
                raise ValueError(f'Could not start the artifact server. See {log}')
    return running['url'] + ('?artifact=' + quote(key) if key else '')
