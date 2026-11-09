import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'skills/codex-studio'
sys.path.insert(0, str(SKILL / 'scripts'))
from model import Conflict, Project, fingerprint
from images import apply_image, prepare_image

try:
    from PIL import Image
except ImportError:
    Image = None


@unittest.skipUnless(Image, 'Pillow required for image composition')
class Images(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = Project(self.root)
        source = Image.new('RGBA', (40, 20))
        source.putdata([(x*5, y*10, 50, (x+y)*4) for y in range(20) for x in range(40)])
        source.save(self.root / 'poster.png')
        self.source_bytes = (self.root / 'poster.png').read_bytes()
        self.art = self.project.add({'id':'poster','kind':'image','title':'포스터','file':'poster.png'})
        self.selection = {'kind':'rect','x':.25,'y':.25,'width':.5,'height':.5,
                          'image_width':40,'image_height':20,'source_sha256':self.art['fingerprints']['file']}
        draft = self.project.review('poster')
        draft['notes'] = [{'id':'change-1','frame':None,'author':'human','text':'선택한 부분을 초록색으로',
                           'selection':copy.deepcopy(self.selection)}]
        self.project.save_review('poster', draft, 0)

    def cli(self, *args):
        return json.loads(subprocess.check_output([sys.executable,str(SKILL/'scripts/artifact.py'),
            '--project',str(self.root),*args],encoding='utf-8'))

    def test_full_candidate_changes_only_selected_pixels_and_preserves_original(self):
        prepared = self.cli('image','prepare','poster','change-1','--out','edits/request-1')
        self.assertEqual(prepared['pixel_bounds'],[10,5,30,15])
        with Image.open(self.root/'edits/request-1/mask.png') as mask:
            self.assertEqual(mask.histogram()[255], 200)
        with Image.open(self.root/'edits/request-1/crop.png') as crop:
            self.assertEqual(crop.size,(20,10))
        candidate = Image.new('RGBA',(40,20),(0,255,0,255))
        candidate.save(self.root/'candidate.png')
        self.cli('image','apply','poster','change-1','--request-version',prepared['request_version'],
                 '--edited','candidate.png','--out','result.png')
        with Image.open(self.root/'poster.png') as original, Image.open(self.root/'result.png') as result:
            for y in range(20):
                for x in range(40):
                    expected = (0,255,0,255) if 10 <= x < 30 and 5 <= y < 15 else original.getpixel((x,y))
                    self.assertEqual(result.getpixel((x,y)),expected)
        self.assertEqual((self.root/'poster.png').read_bytes(),self.source_bytes)
        with self.assertRaises(Conflict):
            apply_image(self.project,'poster','change-1','candidate.png','result.png',prepared['request_version'])

    def test_selection_edit_invalidates_completion_and_prepared_candidate(self):
        item = self.project.requests()[0]
        self.project.update_request('poster','change-1',dict(item,status='done',by='claude',
            summary='영역 수정',checks='영역 밖 픽셀 확인',files=[]))
        draft = self.project.review('poster')
        draft['notes'][0]['selection']['x'] = .1
        self.project.save_review('poster',draft,0)
        changed = self.project.requests()[0]
        self.assertEqual(changed['status'],'pending')
        self.assertEqual(changed['history'][0]['selection'],self.selection)
        Image.new('RGBA',(20,10),(0,255,0,255)).save(self.root/'crop.png')
        with self.assertRaises(Conflict):
            apply_image(self.project,'poster','change-1','crop.png','stale.png',item['request_version'])
        self.assertFalse((self.root/'stale.png').exists())
        apply_image(self.project,'poster','change-1','crop.png','crop-result.png',changed['request_version'])

    def test_selection_validation_points_and_source_identity(self):
        base = self.project.review('poster')
        for invalid in ({'x':float('nan')},{'x':True},{'width':0},{'x':.75},
                        {'image_width':0},{'kind':'object'},{'source_sha256':'0'*64}):
            draft = copy.deepcopy(base)
            draft['notes'][0]['selection'].update(invalid)
            with self.assertRaises(ValueError):
                self.project.save_review('poster',draft,0)
        base['notes'][0]['selection'] = {key:value for key,value in self.selection.items() if key not in ('width','height')}
        base['notes'][0]['selection']['kind'] = 'point'
        saved = self.project.save_review('poster',base,0)
        self.assertEqual(saved['notes'][0]['selection']['kind'],'point')
        with self.assertRaisesRegex(ValueError,'point'):
            prepare_image(self.project,'poster','change-1','point-edit')
        Image.new('RGB',(40,20),'red').save(self.root/'poster.png')
        with self.assertRaises(Conflict):
            self.project.save_review('poster',saved,0)

    def test_legacy_images_bind_selection_to_exact_source(self):
        registration = self.project.storage('artifacts','poster.json')
        data = json.loads(registration.read_text())
        del data['fingerprints']
        registration.write_text(json.dumps(data),encoding='utf-8')
        self.assertEqual(self.project.artifact('poster')['fingerprints']['file'],fingerprint(self.root/'poster.png'))
        Image.new('RGB',(40,20),'red').save(self.root/'poster.png')
        with self.assertRaises(Conflict):
            self.project.save_review('poster',self.project.review('poster'),0)


class Migration(unittest.TestCase):
    def test_legacy_install_preserves_records_and_old_entry_point(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = Project(root)
            project.init()
            (root/'preview.html').write_text('hello',encoding='utf-8')
            project.add({'kind':'html','id':'page','title':'Page','file':'preview.html'})
            from artifact import handoff_instructions, install
            for directory, role in (('.agents','codex'),('.claude','claude')):
                legacy = root/directory/'skills/codex-artifacts'
                (legacy/'scripts').mkdir(parents=True)
                (legacy/'SKILL.md').write_text('---\nname: codex-artifacts\n---\nOld instructions',encoding='utf-8')
                (legacy/'scripts/artifact.py').write_text('print("old")',encoding='utf-8')
                doc = root/('AGENTS.md' if role == 'codex' else 'CLAUDE.md')
                doc.write_text('User instructions\n',encoding='utf-8')
                doc.write_bytes(handoff_instructions(doc,role,str(legacy/'scripts/artifact.py'))[1])
            records = project.storage('artifacts','page.json').read_bytes()
            with project.lock():
                install(project,'both',True)
            self.assertEqual(records,project.storage('artifacts','page.json').read_bytes())
            for directory in ('.agents','.claude'):
                legacy = root/directory/'skills/codex-artifacts'
                self.assertFalse((legacy/'SKILL.md').exists())
                self.assertTrue((legacy/'SKILL.legacy.md').exists())
                output = subprocess.check_output([sys.executable,str(legacy/'scripts/artifact.py'),'list'],cwd=root)
                self.assertEqual(json.loads(output)[0]['id'],'page')
                self.assertTrue((root/directory/'skills/codex-studio/references/image-edits.md').exists())
            for doc in (root/'AGENTS.md',root/'CLAUDE.md'):
                text = doc.read_text(encoding='utf-8')
                self.assertTrue(text.startswith('User instructions\n'))
                self.assertEqual(text.count('<!-- codex-artifacts:handoff:start -->'),1)
                self.assertIn('skills/codex-studio/scripts/artifact.py',text)


if __name__ == '__main__':
    unittest.main()
