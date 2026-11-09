#!/usr/bin/env python3
"""Download and install the self-contained skill without Git or pip."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = 'deepdivekr/codex-studio'
MAX_DOWNLOAD = 50 * 1024 * 1024


def extract_skill(data, destination):
    """Extract only the skill, rejecting unsafe archive entries before writing."""
    target = Path(destination).resolve()
    members = []
    seen = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if len(path.parts) < 4 or path.parts[1:3] != ('skills', 'codex-studio'):
                continue
            if info.is_dir():
                continue
            relative = Path(*path.parts[3:])
            if (path.is_absolute() or '..' in path.parts or '\\' in info.filename
                    or ':' in info.filename or stat.S_ISLNK(info.external_attr >> 16)
                    or not (target / relative).resolve().is_relative_to(target)):
                raise ValueError('The downloaded skill contains an unsafe file path')
            normalized = relative.as_posix().casefold()
            if normalized in seen:
                raise ValueError('The downloaded skill contains duplicate file names')
            seen.add(normalized)
            total += info.file_size
            if total > 100 * 1024 * 1024 or len(members) >= 2000:
                raise ValueError('The downloaded skill exceeds the installation size limit')
            members.append((info, relative))
        if not {'skill.md', 'scripts/artifact.py'}.issubset(seen):
            raise ValueError('The download does not contain the Codex Studio skill')
        for info, relative in members:
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(archive.read(info))
    return target


def download(ref):
    url = f'https://codeload.github.com/{REPOSITORY}/zip/{quote(ref, safe="")}'
    request = Request(url, headers={'User-Agent': 'Codex-Studio-Installer'})
    with urlopen(request, timeout=45) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError('The download exceeds the installation size limit')
    return data


def main(argv=None):
    if sys.version_info < (3, 10):
        raise ValueError('Python 3.10 or newer is required')
    parser = argparse.ArgumentParser(description='Install or update Codex Studio in this project')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--for', dest='agent', choices=('both', 'codex', 'claude'), default='both')
    parser.add_argument('--ref', default='main', help='GitHub branch, tag or commit to install')
    parser.add_argument('--archive', type=Path, help='Use a local source ZIP instead of downloading')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--studio-only', action='store_true', help='Install Studio without production skill packs')
    selection.add_argument('--bundle', action='append', default=None,
                        choices=('remotion', 'hyperframes', 'pixijs', 'motion', 'gl-transitions', 'storyboarding', 'anatomy-reveal', 'colorfigures'),
                        help='Install only these packs instead of all eight (repeatable; no runtimes)')
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('The project path must be a directory')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,199}', args.ref):
        raise ValueError('Use a GitHub branch, tag or commit as --ref')
    print('Codex Studio 설치 중…', flush=True)
    data = args.archive.read_bytes() if args.archive else download(args.ref)
    with tempfile.TemporaryDirectory(prefix='codex-studio-') as temporary:
        skill = extract_skill(data, Path(temporary) / 'codex-studio')
        result = subprocess.run([sys.executable, '-X', 'utf8', str(skill / 'scripts/artifact.py'),
                                 '--project', str(project), 'install', '--for', args.agent, '--upgrade'],
                                capture_output=True, text=True, encoding='utf-8')
        if result.returncode:
            raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Skill installation failed')
        packs = ([] if args.studio_only else args.bundle if args.bundle is not None else
                 list(json.loads((skill / 'assets/toolkits.json').read_text(encoding='utf-8'))['packs']))
        if packs:
            result = subprocess.run([sys.executable, '-X', 'utf8', str(skill / 'scripts/toolkit.py'),
                                     '--project', str(project), 'install', *dict.fromkeys(packs),
                                     '--for', args.agent, '--keep-existing'], capture_output=True, text=True, encoding='utf-8')
            if result.returncode:
                raise ValueError('Studio was installed, but production skill packs did not finish. Rerun the same installer to resume: '
                                 + (result.stderr.strip() or result.stdout.strip()))
            print(result.stdout, end='')
    clients = {'both': 'Codex · Claude', 'codex': 'Codex', 'claude': 'Claude'}[args.agent]
    print(f'설치 완료 · {clients}\n프로젝트: {project}\n새 대화에서 “스튜디오 열어줘”라고 요청하세요.\n업데이트도 같은 설치 명령을 사용하면 됩니다.')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except (OSError, ValueError, URLError, zipfile.BadZipFile) as error:
        sys.exit(f'설치하지 못했습니다: {error}')
