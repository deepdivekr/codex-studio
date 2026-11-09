import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('studio_bootstrap', ROOT / 'install.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class OneLineInstall(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / '한글 프로젝트'
        self.project.mkdir()
        self.archive = self.root / 'source.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for file in (ROOT / 'skills/codex-studio').rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts:
                    archive.write(file, 'codex-studio-main/' + file.relative_to(ROOT).as_posix())
            archive.writestr('codex-studio-main/private.mp4', b'not a skill file')

    def run_install(self, *args, success=True):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'install.py'),
                                 '--archive', str(self.archive), *args], cwd=self.project,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_current_folder_installs_both_clients_and_reinstall_preserves_work(self):
        (self.project / 'AGENTS.md').write_bytes('# 기존 지침\r\n'.encode())
        output = self.run_install().stdout
        self.assertIn('설치 완료', output)
        instructions = {name: (self.project / name).read_bytes() for name in ('AGENTS.md', 'CLAUDE.md')}
        for client in ('.agents', '.claude'):
            skill = self.project / client / 'skills/codex-studio'
            self.assertTrue((skill / 'SKILL.md').is_file())
            self.assertTrue((skill / 'references/image-edits.md').is_file())
            result = subprocess.check_output([sys.executable, str(skill / 'scripts/artifact.py'), 'list'],
                                              cwd=self.project, encoding='utf-8')
            self.assertEqual(json.loads(result), [])
        self.assertTrue(instructions['AGENTS.md'].startswith('# 기존 지침\r\n'.encode()))
        self.assertFalse((self.project / 'private.mp4').exists())
        review = self.project / '.codex-artifacts/reviews/photo.json'
        review.parent.mkdir(parents=True)
        review.write_bytes(b'{"notes":["keep my edits"]}')
        custom = self.project / '.agents/skills/codex-studio/custom.txt'
        custom.write_bytes(b'local extension')
        self.run_install()
        self.assertEqual(review.read_bytes(), b'{"notes":["keep my edits"]}')
        self.assertEqual(custom.read_bytes(), b'local extension')
        self.assertEqual(instructions, {name: (self.project / name).read_bytes() for name in instructions})

    def test_explicit_target_and_single_client(self):
        target = self.root / 'another project'
        target.mkdir()
        self.run_install('--project', str(target), '--for', 'claude')
        self.assertTrue((target / '.claude/skills/codex-studio/SKILL.md').is_file())
        self.assertFalse((target / '.agents').exists())
        self.assertFalse((self.project / '.codex-artifacts').exists())

    def test_bad_download_leaves_project_untouched(self):
        (self.project / 'AGENTS.md').write_bytes(b'keep existing instructions')
        self.archive.write_bytes(b'not a ZIP file')
        result = self.run_install(success=False)
        self.assertIn('설치하지 못했습니다', result.stderr)
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), b'keep existing instructions')
        self.assertEqual([p.name for p in self.project.iterdir()], ['AGENTS.md'])

    def test_unsafe_archive_entries_are_rejected_before_extraction(self):
        for name, symlink in [('codex-studio-main/skills/codex-studio/../../escape.py', False),
                              ('codex-studio-main/skills/codex-studio/link', True),
                              ('codex-studio-main/skills/codex-studio/SKILL.MD', False)]:
            with self.subTest(name=name):
                data = io.BytesIO()
                with zipfile.ZipFile(data, 'w') as archive:
                    archive.writestr('codex-studio-main/skills/codex-studio/SKILL.md', 'skill')
                    archive.writestr('codex-studio-main/skills/codex-studio/scripts/artifact.py', 'script')
                    info = zipfile.ZipInfo(name)
                    if symlink:
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(info, 'outside')
                destination = self.root / 'extracted'
                with self.assertRaises(ValueError):
                    bootstrap.extract_skill(data.getvalue(), destination)
                self.assertFalse(destination.exists())
                self.assertFalse((self.root / 'escape.py').exists())

    @unittest.skipUnless(os.name == 'nt', 'PowerShell installer runs on Windows')
    def test_powershell_passes_project_to_the_downloaded_installer(self):
        shells = [shell for name in ('powershell', 'pwsh') if (shell := shutil.which(name))]
        if not shells:
            self.skipTest('PowerShell unavailable')
        stub = self.root / 'bootstrap-stub.py'
        stub.write_text('import json, sys\nfrom pathlib import Path\n'
                        'target = Path(sys.argv[sys.argv.index("--project") + 1])\n'
                        '(target / "received.json").write_text(json.dumps(sys.argv), encoding="utf-8")\n',
                        encoding='utf-8')
        command = '''
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    Copy-Item -LiteralPath $env:STUDIO_INSTALL_TEST_STUB -Destination $OutFile
}
$before = $ErrorActionPreference
Get-Content -Raw -LiteralPath $env:STUDIO_INSTALL_TEST_SCRIPT | Invoke-Expression
if ($before -ne $ErrorActionPreference) { throw 'Installer changed the parent shell preferences' }
'''
        for shell in shells:
            with self.subTest(shell=shell):
                receipt = self.project / 'received.json'
                receipt.unlink(missing_ok=True)
                env = dict(os.environ, STUDIO_INSTALL_TEST_STUB=str(stub),
                           STUDIO_INSTALL_TEST_SCRIPT=str(ROOT / 'install.ps1'))
                result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', command],
                                        cwd=self.project, env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                self.assertTrue(receipt.exists(), result.stdout.decode(errors='replace'))
                self.assertEqual(json.loads(receipt.read_text(encoding='utf-8'))[1:],
                                 ['--project', str(self.project)])


if __name__ == '__main__':
    unittest.main()
