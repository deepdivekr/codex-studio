from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SKILL = Path(__file__).resolve().parents[1] / 'skills/codex-artifacts'
sys.path.insert(0, str(SKILL / 'scripts'))
from media import load_cues, render
from model import Conflict, Project
from server import Server, server_status


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = Project(self.root)
        (self.root / 'preview.html').write_text('<button>Preview</button>', encoding='utf-8')
        (self.root / 'style.css').write_text('button{color:red}', encoding='utf-8')
        (self.root / 'private.json').write_text('{"private":true}', encoding='utf-8')
        self.project.add({'id': 'design', 'kind': 'html', 'file': 'preview.html',
                          'title': 'Design review', 'asset': ['style.css']})

    def cli(self, *args):
        result = subprocess.check_output([sys.executable, str(SKILL / 'scripts/artifact.py'),
                                          '--project', str(self.root), *args], encoding='utf-8')
        return result.strip() if args[0] in ("init", "export-srt", "render", "open") else json.loads(result)

    def test_open_starts_once_and_returns_selected_artifact_url(self):
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                links = list(executor.map(lambda _: self.cli('open', 'design'), range(2)))
            self.assertEqual(links[0], links[1])
            self.assertTrue(links[0].endswith('/?artifact=design'))
            info = self.cli('status')
            self.assertTrue(info['running'])
            with urlopen(info['url'] + 'api/artifacts/design', timeout=5) as response:
                self.assertEqual(json.load(response)['artifact']['id'], 'design')
            self.assertEqual(self.cli('open'), info['url'])
            self.assertEqual(self.cli('status')['instance'], info['instance'])
        finally:
            info = server_status(self.project)
            if info['running']:
                os.kill(info['pid'], signal.SIGTERM)
                for _ in range(50):
                    if not server_status(self.project)['running']:
                        break
                    time.sleep(.1)

    def test_open_unknown_artifact_does_not_start_server(self):
        from server import open_workspace
        with self.assertRaises(FileNotFoundError):
            open_workspace(self.project, 'missing')
        self.assertFalse(server_status(self.project)['running'])

    def test_cli_agents_read_the_same_handoff_and_reply(self):
        if shutil.which("git"):
            subprocess.run(["git","init","-q","-b","main",str(self.root)],check=True)
            subprocess.run(["git","-C",str(self.root),"-c","user.name=Artifact Test",
                            "-c","user.email=test@example.invalid","commit","-qm","Fixture",
                            "--allow-empty"],check=True)
        outgoing = self.cli('handoff', 'add', '--from', 'codex', '--to', 'claude', '--title', '다음 컷',
                            '--summary', 'Revised the shot', '--next', 'Check the note',
                            '--artifact', 'design', '--file', 'preview.html')
        record_id = outgoing['id']
        if shutil.which('git'):
            self.assertEqual(outgoing['branch'], 'main')
            self.assertRegex(outgoing['commit'], r'^[0-9a-f]{40,64}$')
        self.assertEqual(self.cli('handoff', 'list', '--to', 'claude', '--pending')[0]['id'], record_id)
        self.assertEqual(self.cli('handoff', 'show', record_id)['review_revision'], 0)
        with self.assertRaises(ValueError):
            self.project.acknowledge(record_id, 'codex')
        self.cli('handoff', 'ack', record_id, '--by', 'claude')
        self.assertEqual(self.cli('handoff', 'list', '--to', 'claude', '--pending'), [])
        self.assertEqual(self.cli('handoff', 'list', '--to', 'claude', '--open')[0]['id'], record_id)
        reply = self.cli('handoff', 'add', '--from', 'claude', '--to', 'codex', '--title', 'Reviewed',
                         '--summary', 'Preview loaded', '--next', 'Check on mobile', '--reply-to', record_id)
        self.assertEqual(self.cli('handoff', 'list', '--to', 'codex')[0]['reply_to'], record_id)
        self.assertEqual(self.cli('handoff', 'list', '--to', 'claude', '--open'), [])
        self.assertEqual(self.cli('handoff', 'list', '--to', 'codex', '--open')[0]['id'], reply['id'])
        self.assertIsNone(reply['acknowledgment'])

    def test_two_saves_from_same_revision_cannot_overwrite(self):
        original = self.project.review('design')
        notes = [{'id': 'note-1', 'author': 'human', 'frame': None, 'text': 'Check mobile'}]
        attempts = (dict(original, notes=notes), original)
        def save(change):
            try:
                return self.project.save_review('design', change, 0)['revision']
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(save, attempts))
        self.assertCountEqual(results, [1, 'conflict'])
        self.assertEqual(self.project.review('design')['revision'], 1)

    def test_server_restricts_preview_files_and_post_origin(self):
        with Server(self.project, 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                with urlopen(base, timeout=5) as response:
                    token = re.search(r'name="artifact-token" content="([^"]+)', response.read().decode())[1]
                with urlopen(base + '/preview/design/preview.html', timeout=5) as response:
                    self.assertIn('sandbox allow-scripts', response.headers['Content-Security-Policy'])
                request = Request(base + '/preview/design/style.css', headers={'Range': 'bytes=0-5'})
                with urlopen(request, timeout=5) as response:
                    self.assertEqual((response.status, response.read()), (206, b'button'))
                for route in ('/preview/design/private.json', '/preview/design/%2e%2e/private.json'):
                    with self.assertRaises(HTTPError) as error:
                        urlopen(base + route, timeout=5)
                    self.assertEqual(error.exception.code, 404)
                path = base + '/api/artifacts/design'
                body = json.dumps(self.project.review('design')).encode()
                headers = {'Origin': 'http://example.test', 'Content-Type': 'application/json',
                           'X-Artifact-Token': token}
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(path, data=body, headers=headers), timeout=5)
                self.assertEqual(error.exception.code, 403)
                headers['Origin'] = base
                with urlopen(Request(path, data=body, headers=headers), timeout=5) as response:
                    self.assertEqual(json.load(response)['revision'], 1)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_install_both_read_the_same_project_records(self):
        old_codex = '# 기존 지침\r\n\r\nRun the test suite.\r\n'.encode()
        old_claude = b'# Existing Claude guidance\n'
        (self.root / 'AGENTS.md').write_bytes(old_codex)
        (self.root / 'AGENTS.override.md').write_bytes(b'# Existing override\n')
        (self.root / 'CLAUDE.md').write_bytes(old_claude)
        outgoing = self.cli('handoff', 'add', '--from', 'codex', '--to', 'claude', '--title', 'Ready',
                            '--summary', 'Prepared the preview', '--next', 'Review the title card')
        locations = self.cli('install')
        for location in locations:
            path = Path(location)
            self.assertTrue((path / 'SKILL.md').is_file())
            records = subprocess.check_output([sys.executable, str(path / 'scripts/artifact.py'),
                                               'list'], cwd=self.root, encoding='utf-8')
            self.assertEqual(json.loads(records)[0]['id'], 'design')
        for doc, role, prefix in [('AGENTS.md', 'codex', old_codex),
                                  ('AGENTS.override.md', 'codex', b'# Existing override\n'),
                                  ('CLAUDE.md', 'claude', old_claude)]:
            path = self.root / doc
            before = path.read_bytes()
            self.assertTrue(before.startswith(prefix))
            commands = re.findall(r'^\x60python3 (.+ handoff list .+)\x60$',
                                  path.read_text(encoding='utf-8'), re.M)
            self.assertEqual(len(commands), 1)
            inbox = json.loads(subprocess.check_output([sys.executable, *shlex.split(commands[0])],
                                                       cwd=self.root, encoding='utf-8'))
            self.assertEqual([row['id'] for row in inbox], [outgoing['id']] if role == 'claude' else [])
        originals = {path: path.read_bytes() for path in self.root.glob('*.md')}
        self.cli('install', '--upgrade')
        self.assertEqual({path: path.read_bytes() for path in originals}, originals)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required for export')
    def test_export_reads_edits_and_rejects_replaced_source(self):
        video = self.root / 'cut.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=320x180:r=24:d=2',
                        '-f','lavfi','-i','sine=frequency=440:duration=2',
                        '-c:v','libx264','-c:a','aac','-shortest',str(video)],check=True)
        music = self.root / 'bed.wav'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=250:duration=2',
                        str(music)],check=True)
        captions = self.root / 'captions.srt'
        captions.write_text('1\n00:00:00,100 --> 00:00:01,800\nOriginal\n', encoding='utf-8')
        art = self.project.add({'id':'cut','kind':'video','title':'Cut','file':'cut.mp4','fps':None,
                                'captions':'captions.srt','music':'bed.wav','mask':19,'music_level':60})
        self.assertEqual(art['fps'],'24')
        draft = self.project.review('cut')
        draft['captions']['0'] = 'Edited'
        draft['music'] = 0
        self.project.save_review('cut',draft,1)
        self.cli('export-srt','cut','--out','review.srt')
        self.assertIn('Edited',(self.root / 'review.srt').read_text())
        output = render(self.project,'cut','out.mp4','sans-serif')
        tracks = subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type',
                                          '-of','csv=p=0',str(output)],text=True)
        self.assertEqual(set(tracks.splitlines()),{'video','audio'})
        self.assertNotEqual(video.read_bytes(),output.read_bytes())
        with self.assertRaises(Conflict):
            render(self.project,'cut','out.mp4','sans-serif')
        captions.write_text('changed',encoding='utf-8')
        with self.assertRaises(Conflict):
            load_cues(self.project,art)


if __name__ == '__main__':
    unittest.main()
