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

SKILL = Path(__file__).resolve().parents[1] / 'skills/codex-studio'
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

    def test_saved_requests_keep_completion_separate_and_invalidate_changed_comments(self):
        draft = self.project.review('design')
        draft['notes'] = [{'id':'change-1', 'author':'human', 'frame':None, 'text':'버튼을 크게'}]
        saved = self.project.save_review('design', draft, 0)
        request = self.cli('requests', 'list', '--open')[0]
        self.assertEqual(request['status'], 'pending')
        updated = self.cli('requests', 'update', 'design', 'change-1', '--revision', '0',
                           '--request-version', request['request_version'], '--by', 'codex',
                           '--status', 'done', '--summary', '버튼 크기 변경', '--checks', '모바일 클릭 확인',
                           '--file', 'preview.html', '--result-artifact', 'design')
        self.assertEqual(updated['status'], 'done')
        self.assertEqual(self.cli('requests', 'list', '--open'), [])
        # A human's existing draft can still save without erasing the agent's result.
        saved = self.project.save_review('design', saved, 0)
        self.assertEqual(self.project.requests()[0]['status'], 'done')
        saved['notes'][0]['text'] = '버튼을 더 크게'
        self.project.save_review('design', saved, 0)
        changed = self.project.requests()[0]
        self.assertEqual(changed['status'], 'pending')
        self.assertEqual(len(changed['history']), 1)
        with self.assertRaises(Conflict):
            self.project.update_request('design','change-1', dict(updated, revision=1))
        with self.assertRaises(ValueError):
            self.project.update_request('design','change-1', dict(changed, status='done', by='claude', summary='Done', checks=''))
        body = dict(changed, status='done', by='claude', summary='확대 완료', checks='확인 완료')
        def finish(_):
            try:
                return self.project.update_request('design', 'change-1', body)['status']
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(finish, range(2))), ['done', 'conflict'])

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
                draft = self.project.review('design')
                draft['notes'] = [{'id':'http-note','frame':None,'author':'human','text':'Revise'}]
                self.project.save_review('design', draft, 0)
                with urlopen(base + '/api/requests', timeout=5) as response:
                    item = json.load(response)[0]
                body = json.dumps(dict(item, status='done', by='codex', summary='Updated', checks='Checked')).encode()
                with urlopen(Request(base + '/api/requests/design/http-note', data=body, headers=headers), timeout=5) as response:
                    self.assertEqual(json.load(response)['status'], 'done')
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

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required for audio test')
    def test_export_preserves_audio_tail_after_last_video_frame(self):
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=24:d=1',
                        '-f','lavfi','-i','sine=frequency=440:duration=1.15','-c:v','libx264','-c:a','aac',
                        str(self.root/'tail.mp4')],check=True)
        self.project.add({'id':'tail','kind':'video','file':'tail.mp4','title':'Tail','fps':'24','mask':0,'music_level':100})
        output=render(self.project,'tail','tail-export.mp4','sans-serif')
        def duration(path):
            return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
                                                   '-of','default=nw=1:nk=1',str(path)],text=True))
        self.assertAlmostEqual(duration(output),duration(self.root/'tail.mp4'),delta=.03)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required for audio test')
    def test_three_audio_layers_render_only_selected_sound(self):
        import array
        import math
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=24:d=1',
                        '-c:v','libx264',str(self.root/'layers.mp4')],check=True)
        for name, freq in [('voice',220),('music',440),('effects',660)]:
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'sine=frequency={freq}:duration=1',
                            str(self.root/(name+'.wav'))],check=True)
        art = self.project.add({'id':'layers','kind':'video','file':'layers.mp4','title':'Layers',
                                'fps':'24','mask':0,'music_level':100,'voice':'voice.wav','music':'music.wav'})
        draft = self.project.review('layers')
        draft['notes'] = [{'id':'frame-1','author':'human','frame':6,'text':'효과음 조절'}]
        saved = self.project.save_review('layers', draft, 0)
        self.project.attach_audio('layers', {'effects':'effects.wav'})
        with self.assertRaises(Conflict):
            self.project.save_review('layers', saved, 0)
        self.assertEqual(self.project.review('layers')['notes'], saved['notes'])
        review = self.project.review('layers')
        review.update(voice=0, music=0, effects=100)
        self.project.save_review('layers', review, 0)
        output = render(self.project,'layers','effects-only.mp4','sans-serif')
        raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-vn','-ac','1','-ar','8000','-f','f32le','-'])
        samples = array.array('f',raw)
        def energy(freq):
            return abs(sum(value * complex(math.cos(2*math.pi*freq*i/8000), math.sin(2*math.pi*freq*i/8000))
                           for i,value in enumerate(samples)))
        self.assertGreater(energy(660), 30 * max(energy(220), energy(440)))
        old_rev = self.project.review('layers')['saved_rev']
        self.project.publish_version('layers', old_rev, 'effects-only.mp4', 'Effects only', 'Verified frequencies', 'codex')
        preserved = self.project.version_video('layers', old_rev).read_bytes()
        with self.assertRaises(Conflict):
            self.project.publish_version('layers', old_rev, 'effects-only.mp4', 'Replace', 'Checked', 'codex')
        review = self.project.review('layers'); review['effects'] = 0
        self.project.save_review('layers', review, 0)
        output = render(self.project,'layers','muted.mp4','sans-serif')
        silent = array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-vn','-ac','1','-f','f32le','-']))
        self.assertLess(max(abs(value) for value in silent), .0001)
        new_rev = self.project.review('layers')['saved_rev']
        self.project.publish_version('layers', new_rev, 'muted.mp4', 'All muted', 'Verified silence', 'claude')
        self.assertGreater(new_rev, old_rev)
        # Changing a working output cannot alter a previously archived MP4.
        (self.root/'effects-only.mp4').write_bytes(b'replaced work file')
        self.assertEqual(self.project.version_video('layers', old_rev).read_bytes(), preserved)
        self.assertEqual(self.project.version('layers', old_rev)['review']['effects'], 100)
        self.assertEqual(self.project.version('layers', new_rev)['review']['effects'], 0)
        render(self.project,'layers','from-old-rev.mp4','sans-serif',version=old_rev)
        self.assertEqual(self.project.review('layers')['saved_rev'], new_rev)
        with Server(self.project,0) as server:
            thread=Thread(target=server.serve_forever,daemon=True); thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}/versions/layers/{old_rev}/download'
                with urlopen(Request(url,headers={'Range':'bytes=0-31'}),timeout=5) as response:
                    self.assertEqual(response.status,206)
                    self.assertIn(f'rev{old_rev}.mp4',response.headers['Content-Disposition'])
                    self.assertEqual(response.read(),preserved[:32])
            finally:
                server.shutdown(); thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
