#!/usr/bin/env python3
"""Inspect 30 video tools; install selected, pinned upstream skills, never runtimes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
import uuid

CATALOG = Path(__file__).resolve().parents[1] / 'assets' / 'toolkits.json'
RECEIPT = '.codex-studio-upstream.json'
MAX_FILE = 8 * 1024 * 1024
MAX_PACK = 32 * 1024 * 1024


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe_relative(value):
    p = PurePosixPath(value)
    if (not value or p.is_absolute() or '\\' in value or ':' in value
            or any(x in ('', '.', '..') for x in value.split('/'))
            or any(x.endswith((' ', '.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', x) for x in p.parts)):
        raise ValueError(f'Unsafe skill path: {value}')
    return p


def within(root, relative):
    p = root / Path(*safe_relative(relative).parts)
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Destination escapes project: {relative}')
    q = p
    while q != root:
        if q.is_symlink():
            raise ValueError(f'Symlink destination is not supported: {q}')
        q = q.parent
    return p


def entries(pack):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', pack['repository']) or not re.fullmatch(r'[a-f0-9]{40}', pack['commit']):
        raise ValueError('Invalid pinned repository/commit')
    result, seen = [], set()
    for item in pack['files']:
        safe_relative(item['path'])
        prefix = next((p for p in pack['prefixes'] if item['path'].startswith(p)), None)
        if prefix is None:
            raise ValueError('File is outside selected upstream skills')
        # A shared skills/ prefix preserves every sibling; a single-skill prefix preserves its name.
        parent = prefix.rstrip('/').rpartition('/')[0]
        base = prefix if prefix == 'skills/' else (parent + '/' if parent else '')
        rel = (pack['destination_root'] + '/' + item['path'] if pack.get('destination_root')
               else item['path'][len(base):])
        safe_relative(rel)
        if rel.casefold() in seen:
            raise ValueError('Duplicate destination in toolkit manifest')
        seen.add(rel.casefold())
        if not re.fullmatch(r'[a-f0-9]{40}', item['sha']) or not 0 <= item['size'] <= MAX_FILE:
            raise ValueError('Invalid upstream file hash/size')
        result.append((item, rel))
    if not result or len(result) > 2000 or sum(x['size'] for x, _ in result) > MAX_PACK:
        raise ValueError('Toolkit exceeds file/size budget')
    names = sorted({PurePosixPath(rel).parts[0] for _, rel in result})
    for name in names:
        if f'{name}/SKILL.md'.casefold() not in seen:
            raise ValueError(f'Missing entrypoint: {name}')
    return result, names


def download(pack, item):
    if pack.get('bundled_file'):
        source = within(CATALOG.parent, pack['bundled_file'])
        contents = json.loads(source.read_text(encoding='utf-8'))
        data = contents['files'][item['path']].encode('utf-8')
        if len(data) != item['size'] or blob_sha(data) != item['sha']:
            raise ValueError('Bundled content failed verification: ' + item['path'])
        return data
    url = f'https://raw.githubusercontent.com/{pack["repository"]}/{pack["commit"]}/{quote(item["path"], safe="/")}'
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Codex-Studio-Toolkit'}), timeout=40) as response:
                data = response.read(MAX_FILE + 1)
            break
        except (HTTPError, URLError, TimeoutError) as error:
            if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    if len(data) != item['size'] or blob_sha(data) != item['sha']:
        raise ValueError(f'Upstream content failed verification: {item["path"]}')
    return data


def install_pack(project, name, pack, agent='both', upgrade=False, fetch=download):
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be a directory')
    file_entries, names = entries(pack)
    notices = pack.get('license_files', [])
    for item in notices:
        safe_relative(item['path'])
        if '/' in item['path'] or not 0 <= item['size'] <= MAX_FILE or not re.fullmatch(r'[a-f0-9]{40}', item['sha']):
            raise ValueError('Invalid license notice')
    clients = ['codex', 'claude'] if agent == 'both' else [agent]
    parents = {'codex': '.agents/skills', 'claude': '.claude/skills'}
    targets = [within(project, f'{parents[client]}/{skill}') for client in clients for skill in names]
    if len({str(x.resolve()).casefold() for x in targets}) != len(targets):
        raise ValueError('Skill targets alias each other')
    # Refuse replacing user-managed skills unless the caller deliberately requests upgrade.
    for target in targets:
        if target.exists() and not upgrade:
            receipt = target / RECEIPT
            if not receipt.is_file():
                raise ValueError(f'{target} already exists; review it before using --upgrade')
            old = json.loads(receipt.read_text(encoding='utf-8'))
            if old.get('commit') != pack['commit'] or old.get('repository') != pack['repository']:
                raise ValueError(f'{target} has another version; use --upgrade to preserve a backup')
            for item, rel in file_entries:
                if rel.startswith(target.name + '/'):
                    dest = within(target, rel[len(target.name)+1:])
                    if not dest.is_file() or blob_sha(dest.read_bytes()) != item['sha']:
                        raise ValueError(f'{target} has local changes; use --upgrade to preserve a backup')
    pending = [t for t in targets if not t.exists() or upgrade]
    if not pending:
        return {'pack': name, 'status': 'already_installed', 'skills': names, 'commit': pack['commit']}
    work = within(project, '.codex-studio/toolkit-work')
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=name+'-', dir=work) as temporary:
        stage = Path(temporary)
        # Download and verify the entire pack before touching installed skill folders.
        with ThreadPoolExecutor(max_workers=8) as pool:
            data_items = list(pool.map(lambda item: fetch(pack, item[0]), file_entries))
            notice_data = list(pool.map(lambda item: fetch(pack, item), notices))
        for (item, rel), data in zip(file_entries, data_items):
            if len(data) != item['size'] or blob_sha(data) != item['sha']:
                raise ValueError(f'Content verification failed: {rel}')
            dest = within(stage, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if item.get('executable'):
                dest.chmod(0o755)
        for skill in names:
            for item, data in zip(notices, notice_data):
                if len(data) != item['size'] or blob_sha(data) != item['sha']:
                    raise ValueError('License notice failed verification')
                (stage / skill / ('UPSTREAM-' + item['path'])).write_bytes(data)
            (stage / skill / RECEIPT).write_text(json.dumps({
                'pack': name, 'repository': pack['repository'], 'commit': pack['commit'],
                'source': pack.get('source_url', f'https://github.com/{pack["repository"]}/tree/{pack["commit"]}'),
                'revision_kind': pack.get('revision_kind', 'git-commit'),
                'notice': pack.get('notice', ''),
            }, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        backup = within(project, '.codex-studio/toolkit-backups/' + uuid.uuid4().hex)
        replaced, created = [], []
        try:
            for i, target in enumerate(pending):
                within(project, target.relative_to(project).as_posix())
                if target.exists():
                    backup.mkdir(parents=True, exist_ok=True)
                    saved = backup / str(i)
                    target.rename(saved)
                    replaced.append((target, saved))
                target.parent.mkdir(parents=True, exist_ok=True)
                created.append(target)
                shutil.copytree(stage / target.name, target)
        except Exception:
            for target in reversed(created):
                within(project, target.relative_to(project).as_posix())
                if target.exists():
                    shutil.rmtree(target)
            for target, saved in reversed(replaced):
                saved.rename(target)
            raise
    return {'pack': name, 'status': 'installed', 'skills': names, 'commit': pack['commit'],
            'targets': [str(p) for p in pending], 'backup': str(backup) if replaced else None,
            'runtime_installed': False, 'mcp_configured': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='Show the 30 audited tools and available skill packs')
    p = sub.add_parser('plan', help='Inspect a tool or skill pack without downloads')
    p.add_argument('name')
    p = sub.add_parser('install', help='Download only selected upstream skills at the reviewed commit')
    p.add_argument('packs', nargs='+')
    p.add_argument('--for', dest='agent', choices=('codex', 'claude', 'both'), default='both')
    p.add_argument('--upgrade', action='store_true', help='Back up existing skill folders before replacement')
    args = parser.parse_args(argv)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    if args.command == 'list':
        result = {'checked_at': catalog['checked_at'], 'packs': list(catalog['packs']),
                  'projects': [{k:p[k] for k in ('id','name','decision','capability')} for p in catalog['projects']]}
    elif args.command == 'plan':
        tool = next((p for p in catalog['projects'] if p['id'] == args.name), None)
        pack = catalog['packs'].get(args.name)
        if not tool and not pack:
            raise ValueError('Unknown tool: ' + args.name)
        result = {'project': tool, 'skill_pack': None, 'runtime_action': 'Not installed; choose a project-local toolchain after reviewing official requirements.'}
        if pack:
            files, names = entries(pack)
            result['skill_pack'] = {'repository':pack['repository'],'commit':pack['commit'],'skills':names,'files':len(files),'bytes':sum(x['size'] for x,_ in files),'notice':pack['notice']}
            result['skill_pack']['revision_kind'] = pack.get('revision_kind', 'git-commit')
    else:
        unknown = set(args.packs) - set(catalog['packs'])
        if unknown:
            raise ValueError('No reviewed upstream skill pack for: '+', '.join(sorted(unknown)))
        result = []
        for name in dict.fromkeys(args.packs):
            print(f'Installing pinned {name} skills (no runtime/MCP setup)…', file=sys.stderr, flush=True)
            result.append(install_pack(args.project, name, catalog['packs'][name], args.agent, args.upgrade))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (OSError, ValueError, URLError) as error:
        sys.exit(f'Toolkit action failed: {error}')
