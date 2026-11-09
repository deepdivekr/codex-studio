#!/usr/bin/env python3
"""CLI for Codex Artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from media import destination, edited_cues, format_srt, load_cues, render
from model import Conflict, Project, ROLES, project_root
from server import serve, server_status

SKILL = Path(__file__).resolve().parents[1]


def install(project, agent, upgrade):
    locations = {'codex': '.agents', 'claude': '.claude'}
    paths = []
    for role in locations if agent == 'both' else [agent]:
        location = project.root / locations[role] / 'skills' / SKILL.name
        if not location.resolve().is_relative_to(project.root):
            raise ValueError('Skill destination resolves outside the project')
        if location.exists() and location.resolve() != SKILL and not upgrade:
            raise Conflict(f'{location} already exists. Use --upgrade to replace known skill files.')
        paths.append(location)
    files = [SKILL / 'SKILL.md', SKILL / 'LICENSE', *SKILL.glob('agents/*.yaml'),
             *SKILL.glob('scripts/*.py'), *SKILL.glob('assets/*')]
    for target in paths:
        if target.resolve() == SKILL:
            continue
        for src in files:
            if not src.is_file():
                continue
            dst = target / src.relative_to(SKILL)
            if not dst.resolve().is_relative_to(project.root):
                raise ValueError('Skill file destination resolves outside the project')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    return [str(location) for location in paths]


def parser():
    app = argparse.ArgumentParser(description='Local artifact review and agent handoff')
    app.add_argument('--project', help='Project root (defaults to the nearest Git or artifact root)')
    commands = app.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    commands.add_parser('status', help='Find the existing server for this checkout')
    setup = commands.add_parser('install')
    setup.add_argument('--for', dest='agent', choices=('codex', 'claude', 'both'), default='both')
    setup.add_argument('--upgrade', action='store_true')
    web = commands.add_parser('serve')
    web.add_argument('--port', type=int, default=0)
    add = commands.add_parser('add')
    add.add_argument('kind', choices=('video', 'html', 'image'))
    add.add_argument('id')
    add.add_argument('file', help='Project-relative source path')
    add.add_argument('--title', required=True)
    add.add_argument('--fps', help='Source frame rate, detected with ffprobe if omitted')
    add.add_argument('--captions')
    add.add_argument('--music')
    add.add_argument('--voice', help='Separate voice track; replaces embedded video audio')
    add.add_argument('--music-level', type=int, default=100)
    add.add_argument('--mask', type=int, default=0, help='Cover the bottom N percent of baked captions')
    add.add_argument('--asset', action='append', default=[], help='An allowed relative HTML dependency; repeat as needed')
    commands.add_parser('list')
    review = commands.add_parser('review')
    sub = review.add_subparsers(dest='operation', required=True)
    sub.add_parser('show').add_argument('id')
    save = sub.add_parser('save')
    save.add_argument('id')
    save.add_argument('input', help='JSON from review show, with its revision, or - for stdin')
    export = commands.add_parser('export-srt')
    export.add_argument('id')
    export.add_argument('--out', required=True)
    encode = commands.add_parser('render')
    encode.add_argument('id')
    encode.add_argument('--out', required=True)
    encode.add_argument('--font', default='sans-serif')
    transfer = commands.add_parser('handoff')
    sub = transfer.add_subparsers(dest='operation', required=True)
    queue = sub.add_parser('list')
    queue.add_argument('--to', choices=ROLES)
    queue.add_argument('--pending', action='store_true')
    sub.add_parser('show').add_argument('id')
    ack = sub.add_parser('ack')
    ack.add_argument('id')
    ack.add_argument('--by', choices=ROLES, required=True)
    new = sub.add_parser('add')
    new.add_argument('--from', dest='sender', choices=ROLES, required=True)
    new.add_argument('--to', choices=ROLES, required=True)
    new.add_argument('--title', required=True)
    new.add_argument('--summary', required=True)
    new.add_argument('--next', required=True)
    new.add_argument('--checks', default='')
    new.add_argument('--file', action='append', default=[])
    new.add_argument('--artifact')
    new.add_argument('--reply-to')
    return app


def run(args):
    project = Project(project_root(args.project))
    command = args.command
    if command == 'init':
        project.init()
        return str(project.data)
    if command == 'install':
        return install(project, args.agent, args.upgrade)
    if command == 'status':
        return server_status(project)
    if command == 'serve':
        return serve(project, args.port)
    if command == 'add':
        return project.add(vars(args))
    if command == 'list':
        return project.artifacts()
    if command == 'render':
        return str(render(project, args.id, args.out, args.font))
    if command in ('export-srt', 'review'):
        artifact = project.artifact(args.id)
        if command == 'review' and args.operation == 'show':
            return project.review(args.id)
        cues = load_cues(project, artifact)
        if command == 'export-srt':
            out = destination(project, args.out)
            with out.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(format_srt(edited_cues(cues, project.review(args.id))))
            return str(out)
        source = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8-sig')
        for field in artifact.get('fingerprints', {}):
            project.asset(artifact, field)
        return project.save_review(args.id, json.loads(source), len(cues))
    if args.operation == 'list':
        return project.handoffs(args.to, args.pending)
    if args.operation == 'show':
        return project.handoff(args.id)
    if args.operation == 'ack':
        return project.acknowledge(args.id, args.by)
    return project.create_handoff({'from': args.sender, 'to': args.to, 'title': args.title,
                                   'summary': args.summary, 'next': args.next, 'checks': args.checks,
                                   'files': args.file, 'artifact': args.artifact, 'reply_to': args.reply_to})


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        result = run(parser().parse_args())
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2) if not isinstance(result, str) else result)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
