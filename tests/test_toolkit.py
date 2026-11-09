import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('toolkit', ROOT / 'skills/codex-studio/scripts/toolkit.py')
toolkit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolkit)


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.files = {'skills/demo/SKILL.md': b'---\nname: demo\ndescription: Demo\n---\n',
                      'skills/demo/references/example.md': '한글 영상'.encode(),
                      'LICENSE': b'MIT test notice'}
        self.pack = {'repository': 'test/demo', 'commit': 'a' * 40, 'prefixes': ['skills/demo/'],
                     'files': [{'path': p, 'sha': toolkit.blob_sha(b), 'size': len(b)} for p,b in self.files.items() if p != 'LICENSE'],
                     'license_files': [{'path': 'LICENSE', 'sha': toolkit.blob_sha(self.files['LICENSE']), 'size': len(self.files['LICENSE'])}]}

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self, pack, item):
        return self.files[item['path']]

    def test_install_both_idempotence_and_license(self):
        out = toolkit.install_pack(self.root, 'demo', self.pack, fetch=self.fetch)
        self.assertFalse(out['runtime_installed'])
        for folder in ['.agents', '.claude']:
            target = self.root / folder / 'skills/demo'
            self.assertEqual((target/'references/example.md').read_text(encoding='utf-8'), '한글 영상')
            self.assertEqual((target/'UPSTREAM-LICENSE').read_bytes(), self.files['LICENSE'])
        with patch.object(toolkit, 'download', side_effect=AssertionError('must not download')):
            out = toolkit.install_pack(self.root, 'demo', self.pack, fetch=lambda *a: self.fail())
        self.assertEqual(out['status'], 'already_installed')

    def test_modified_skill_refused_then_backed_up(self):
        toolkit.install_pack(self.root, 'demo', self.pack, fetch=self.fetch)
        target = self.root/'.agents/skills/demo/SKILL.md'
        target.write_text('user custom work', encoding='utf-8')
        with self.assertRaises(ValueError):
            toolkit.install_pack(self.root, 'demo', self.pack, fetch=self.fetch)
        out = toolkit.install_pack(self.root, 'demo', self.pack, upgrade=True, fetch=self.fetch)
        self.assertTrue(any(p.read_text(encoding='utf-8') == 'user custom work' for p in Path(out['backup']).rglob('SKILL.md')))

    def test_hash_failure_does_not_change_existing_skill(self):
        target = self.root/'.agents/skills/demo'
        target.mkdir(parents=True)
        (target/'SKILL.md').write_text('original')
        with self.assertRaises(ValueError):
            toolkit.install_pack(self.root, 'demo', self.pack, upgrade=True, fetch=lambda *a: b'corrupted')
        self.assertEqual((target/'SKILL.md').read_text(), 'original')
        self.assertFalse((self.root/'.claude/skills/demo').exists())

    def test_rollback_after_partial_destination_copy(self):
        toolkit.install_pack(self.root, 'demo', self.pack, fetch=self.fetch)
        original = toolkit.shutil.copytree
        count = 0
        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('disk full')
            return original(*args, **kwargs)
        with patch.object(toolkit.shutil, 'copytree', side_effect=fail_second):
            with self.assertRaises(OSError):
                toolkit.install_pack(self.root, 'demo', self.pack, upgrade=True, fetch=self.fetch)
        for folder in ['.agents', '.claude']:
            self.assertEqual((self.root/folder/'skills/demo/SKILL.md').read_bytes(), self.files['skills/demo/SKILL.md'])

    def test_paths_duplicates_and_symlinks(self):
        for path in ['../x', '/x', 'a/../x', 'a\\x', 'C:x', 'nul.txt', 'a./x']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                toolkit.safe_relative(path)
        pack = copy.deepcopy(self.pack)
        pack['files'].append(dict(pack['files'][0]))
        with self.assertRaises(ValueError):
            toolkit.entries(pack)
        outside = self.root/'outside'
        outside.mkdir()
        try:
            (self.root/'.agents').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):
            toolkit.install_pack(self.root, 'demo', self.pack, fetch=self.fetch)

    def test_shipped_catalog_has_30_distinct_projects_and_valid_packs(self):
        data = json.loads(toolkit.CATALOG.read_text(encoding='utf-8'))
        self.assertEqual(len({p['id'] for p in data['projects']}), 30)
        self.assertEqual(len(data['packs']), 8)
        for pack in data['packs'].values():
            files, names = toolkit.entries(pack)
            self.assertTrue(files and names)

    def test_bundled_snapshot_installs_offline_and_checks_hashes(self):
        data = json.loads(toolkit.CATALOG.read_text(encoding='utf-8'))
        pack = data['packs']['colorfigures']
        with patch.object(toolkit, 'urlopen', side_effect=AssertionError('offline pack')):
            toolkit.install_pack(self.root, 'colorfigures', pack)
        target = self.root/'.agents/skills/colorfigures'
        self.assertTrue((target/'scripts/build.py').is_file())
        self.assertIn('April Zhu', (target/'LICENSE').read_text(encoding='utf-8'))
        broken = copy.deepcopy(pack['files'][0])
        broken['sha'] = '0' * 40
        with self.assertRaises(ValueError):
            toolkit.download(pack, broken)


if __name__ == '__main__':
    unittest.main()
