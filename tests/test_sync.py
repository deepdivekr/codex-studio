from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

SKILL = Path(__file__).resolve().parents[1] / 'skills/codex-artifacts'
sys.path.insert(0, str(SKILL / 'scripts'))
from media import load_cues, render
from model import Conflict, Project
from sync import prepare, probe, render_synced


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class NarrationWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = Project(self.root)
        self.ffmpeg('-f','lavfi','-i','color=c=red:s=160x90:r=30:d=1',
                    '-f','lavfi','-i','color=c=green:s=160x90:r=30:d=0.8',
                    '-f','lavfi','-i','color=c=blue:s=160x90:r=30:d=1.2',
                    '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0',
                    '-c:v','libx264','cut.mp4')
        timeline = {'shots':['room','card:Chapter','street'], 'captions':[
            {'shot':0, 'text':'First line', 'start':0, 'end':1, 'say_end':.85},
            {'shot':1, 'text':'', 'start':1, 'end':1.8},
            {'shot':2, 'text':'Second line', 'start':1.8, 'end':3, 'say_end':2.7}
        ]}
        (self.root / 'old.json').write_text(json.dumps(timeline), encoding='utf-8')
        (self.root / 'clips').mkdir()
        for name, length in [('clips/0001.wav', 1.6), ('clips/0002.wav', .7), ('replacement.wav', 3), ('bed.wav', 1)]:
            with wave.open(str(self.root / name), 'wb') as out:
                out.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                out.writeframes(b'\x02\x00' * round(length * 16000))
        self.artifact = self.project.add({'id':'cut','kind':'video','title':'Cut','file':'cut.mp4','fps':'30',
                                         'captions':'old.json','music':'bed.wav','mask':0,'music_level':60})
        self.cues = load_cues(self.project, self.artifact)
        self.original = [cue['text'] for cue in self.cues]

    def ffmpeg(self, *args):
        return subprocess.check_output(['ffmpeg','-v','error',*args],cwd=self.root)

    def save_script(self):
        review = self.project.review('cut')
        return self.project.save_review('cut', dict(review, mode='script',
            captions={'0':'First line now includes more words'}), len(self.cues))

    def test_approved_draft_controls_render_and_reapproval(self):
        draft = self.save_script()
        with self.assertRaises(Conflict):
            prepare(self.project, 'cut', clips='clips')
        with self.assertRaises(Conflict):
            render(self.project, 'cut', 'plain.mp4', 'sans-serif')
        with self.assertRaises(Conflict):
            self.project.approve_script('cut', draft['revision'] - 1, self.original)
        approval = self.project.approve_script('cut', draft['revision'], self.original)
        self.assertTrue(approval['script_approved'])
        music_change = self.project.save_review('cut', dict(approval, music=40), len(self.cues))
        self.assertTrue(music_change['script_approved'])
        changed = self.project.save_review('cut', dict(music_change, captions={'0':'Further edits'}), len(self.cues))
        self.assertNotIn('script_approved', changed)

    def test_extended_narration_moves_cut_and_preserves_title(self):
        draft = self.save_script()
        self.project.approve_script('cut', draft['revision'], self.original)
        stats, _ = prepare(self.project, 'cut', clips='clips')
        target = stats['cue_starts'][1]['after']
        self.assertAlmostEqual(target, 2.43, places=2)
        self.assertEqual(stats['preserved_title_cards'], 1)
        result = render_synced(self.project, 'cut', 'synced.mp4', 'sans-serif', clips='clips')
        out = Path(result['output'])
        self.assertAlmostEqual(probe(out, 'a:0'), stats['new_seconds'], delta=.05)
        self.assertAlmostEqual(probe(out, 'v:0'), stats['new_seconds'], delta=.07)

        def dominant(time):
            raw = self.ffmpeg('-ss',str(time),'-i',str(out),'-frames:v','1',
                              '-vf','crop=2:2:0:0','-f','rawvideo','-pix_fmt','rgb24','-')
            return max(range(3), key=lambda channel: raw[channel])
        self.assertEqual(dominant(1.4), 0)  # the first picture holds under longer speech
        self.assertEqual(dominant(target - .10), 1)  # title still has its own interval
        self.assertEqual(dominant(target + .04), 2)  # following cut begins with next line

    def test_alignment_must_leave_a_pause_for_the_title(self):
        draft = self.save_script()
        self.project.approve_script('cut', draft['revision'], self.original)
        data = [
            {'start':0, 'end':1.6, 'text':'First line now includes more words'},
            {'start':1.8, 'end':2.9, 'text':'Second line'}
        ]
        (self.root/'timings.json').write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'quiet gap'):
            prepare(self.project, 'cut', voice='replacement.wav', timings='timings.json')
        data[0]['text'] = 'Wrong script'
        (self.root/'timings.json').write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'do not match'):
            prepare(self.project, 'cut', voice='replacement.wav', timings='timings.json')
