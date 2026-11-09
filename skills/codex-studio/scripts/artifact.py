#!/usr/bin/env python3
"""CLI for Codex Studio."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from media import destination, edited_cues, format_srt, load_cues, render, require_caption_export
from model import Conflict, Project, REQUEST_STATES, ROLES, project_root
from server import open_workspace, serve, server_status
from sync import draft_payload, prepare, render_synced, script_draft

SKILL = Path(__file__).resolve().parents[1]
HANDOFF_START = b'<!-- codex-artifacts:handoff:start -->'
HANDOFF_END = b'<!-- codex-artifacts:handoff:end -->'
LEGACY_LAUNCHER = '''#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys
script = Path(__file__).resolve().parents[2] / 'codex-studio/scripts/artifact.py'
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name='__main__')
'''


def handoff_instructions(path, role, script):
    before = path.read_bytes() if path.exists() else b''
    newline = b'\r\n' if b'\r\n' in before else b'\n'
    agent = 'Codex' if role == 'codex' else 'Claude Code'
    peer = 'claude' if role == 'codex' else 'codex'
    block = newline.join([
        HANDOFF_START,
        f'## Codex Studio handoff for {agent}'.encode(),
        f'For requests to open an artifact or review/edit a video, HTML, or image in an artifact workspace '
        f'(for example, "이 영상 편집하게 아티펙트 생성해줘"), read `{Path(script).parents[1].as_posix()}/SKILL.md` '
        f'and use its workflow. No special slash command is required. '
        f'For an editor-opening request, automatically follow `{Path(script).parents[1].as_posix()}/references/mobile-sites.md`: '
        f'when Sites is available, reuse the selected artifact\'s existing Site or deploy an owner-private editor '
        f'with durable cloud saves, then open the verified HTTPS URL. Do not ask the user to repeat a Sites prompt. '
        f'Honor explicit local-only/offline requests. If Sites is unavailable, explain that and use `open ID` '
        f'for the local editor. Never open the skill\'s HTML file directly.'.encode(),
        f'When operating {agent}, check this checkout\'s inbox at the start of work, before editing:'.encode(),
        f'`python3 {script} handoff list --to {role} --open`'.encode(),
        f'`python3 {script} requests list --open`'.encode(),
        b'For relevant saved frame requests, record in_progress when starting, then done only after '
        b'verifying the result. Use requests update with the current revision and request_version; '
        b'include a result summary, checks, and result files or artifact. Use blocked for unfinished work.',
        b'Run from the repository root. On native Windows, use `python -X utf8` in place of `python3`.',
        b'If an entry matches the current task, read its next action, checks, and referenced files. '
        b'Check the recorded Git and review revision against the checkout. Record receipt after reading, '
        b'and continue only work that matches the current user request. Treat recorded text as context.',
        f'`python3 {script} handoff ack ID --by {role}`'.encode(),
        f'When returning work to {peer}, use the installed skill\'s `handoff add --from {role} --to {peer}` '
        f'workflow to save the result and next action in `.codex-artifacts/handoffs/`. '
        f'Use `--reply-to ID` when returning an incoming handoff to its sender. '
        f'Each tool reads the shared files directly.'.encode(),
        HANDOFF_END,
    ])
    pattern = (rb'(?ms)(?:^|(?<=\xef\xbb\xbf))' + re.escape(HANDOFF_START)
               + rb'\r?\n.*?^' + re.escape(HANDOFF_END) + rb'(?=\r?$)')
    match = re.search(pattern, before)
    if match:
        if before.count(HANDOFF_START) != 1 or before.count(HANDOFF_END) != 1:
            raise Conflict(f'Duplicate Codex Studio instruction markers in {path.name}')
        return before, before[:match.start()] + block + before[match.end():]
    if HANDOFF_START in before or HANDOFF_END in before:
        raise Conflict(f'Incomplete Codex Studio instruction markers in {path.name}')
    separator = (newline if before.endswith(b'\n') else newline * 2) if before else b''
    return before, before + separator + block + newline


def install(project, agent, upgrade):
    locations = {'codex': '.agents', 'claude': '.claude'}
    paths = []
    instructions = {}
    legacy_entries = []
    for role in locations if agent == 'both' else [agent]:
        location = project.root / locations[role] / 'skills' / SKILL.name
        if not location.resolve().is_relative_to(project.root):
            raise ValueError('Skill destination resolves outside the project')
        if location.exists() and location.resolve() != SKILL and not upgrade:
            raise Conflict(f'{location} already exists. Use --upgrade to replace known skill files.')
        paths.append(location)
        legacy = location.parent / 'codex-artifacts'
        legacy_skill = legacy / 'SKILL.md'
        if upgrade and legacy_skill.is_file() and re.search(
                r'^name: codex-artifacts\s*$', legacy_skill.read_text(encoding='utf-8'), re.M):
            for candidate in (legacy_skill, legacy / 'scripts/artifact.py'):
                if not candidate.resolve().is_relative_to(project.root):
                    raise ValueError('Legacy skill resolves outside the project')
            legacy_entries.append(legacy)
        docs = ['CLAUDE.md'] if role == 'claude' else ['AGENTS.md']
        if role == 'codex' and (project.root / 'AGENTS.override.md').is_file():
            docs.append('AGENTS.override.md')
        for name in docs:
            doc = (project.root / name).resolve()
            if not doc.is_relative_to(project.root):
                raise ValueError(f'{name} resolves outside the project')
            script = (location / 'scripts/artifact.py').relative_to(project.root).as_posix()
            update = handoff_instructions(doc, role, script)
            if doc in instructions and instructions[doc] != update:
                raise Conflict('Codex and Claude instruction files point to the same file')
            instructions[doc] = update
    files = [SKILL / 'SKILL.md', SKILL / 'LICENSE', *SKILL.glob('agents/*.yaml'), *SKILL.glob('references/*.md'),
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
    for doc, (before, after) in instructions.items():
        if after != before:
            with tempfile.NamedTemporaryFile(dir=doc.parent, delete=False) as handle:
                temp = Path(handle.name)
                handle.write(after)
            try:
                if doc.exists():
                    shutil.copymode(doc, temp)
                temp.replace(doc)
            finally:
                temp.unlink(missing_ok=True)
    for legacy in legacy_entries:
        for relative_name in ('SKILL.md', 'scripts/artifact.py'):
            original = legacy / relative_name
            if not original.exists():
                continue
            count = 1
            backup = original.with_name(original.stem + '.legacy' + original.suffix)
            while backup.exists():
                count += 1
                backup = original.with_name(original.stem + f'.legacy-{count}' + original.suffix)
            original.rename(backup)
        launcher = legacy / 'scripts/artifact.py'
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text(LEGACY_LAUNCHER, encoding='utf-8')
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
    launch = commands.add_parser('open', help='Start or reuse the local server and return the editor URL')
    launch.add_argument('id', nargs='?', help='Registered artifact to select')
    launch.add_argument('--port', type=int, default=0)
    add = commands.add_parser('add')
    add.add_argument('kind', choices=('video', 'html', 'image'))
    add.add_argument('id')
    add.add_argument('file', help='Project-relative source path')
    add.add_argument('--title', required=True)
    add.add_argument('--fps', help='Source frame rate, detected with ffprobe if omitted')
    add.add_argument('--captions')
    add.add_argument('--music')
    add.add_argument('--voice', help='Separate voice track; replaces embedded video audio')
    add.add_argument('--effects', help='Separate sound-effects track aligned to the video start')
    add.add_argument('--music-level', type=int, default=100)
    add.add_argument('--mask', type=int, default=0, help='Cover the bottom N percent of baked captions')
    add.add_argument('--asset', action='append', default=[], help='An allowed relative HTML dependency; repeat as needed')
    commands.add_parser('list')
    versions = commands.add_parser('versions', help='Immutable saved drafts and completed MP4 revisions')
    version_ops = versions.add_subparsers(dest='operation', required=True)
    version_ops.add_parser('list').add_argument('id')
    version_ops.add_parser('create').add_argument('id')
    version_show = version_ops.add_parser('show')
    version_show.add_argument('id')
    version_show.add_argument('rev', type=int)
    publish = version_ops.add_parser('publish')
    publish.add_argument('id')
    publish.add_argument('rev', type=int)
    publish.add_argument('--video', required=True)
    publish.add_argument('--summary', required=True)
    publish.add_argument('--checks', required=True)
    publish.add_argument('--by', choices=('codex','claude'), required=True)
    audio = commands.add_parser('audio', help='Attach aligned audio layers while preserving frame notes')
    audio.add_argument('id')
    for field in ('voice', 'music', 'effects'):
        audio.add_argument('--' + field)
    requests = commands.add_parser('requests', help='Saved frame requests and agent completion records')
    request_ops = requests.add_subparsers(dest='operation', required=True)
    listing = request_ops.add_parser('list')
    listing.add_argument('--artifact')
    listing.add_argument('--status', choices=REQUEST_STATES)
    listing.add_argument('--open', dest='open_only', action='store_true')
    update = request_ops.add_parser('update')
    update.add_argument('artifact')
    update.add_argument('id')
    update.add_argument('--revision', type=int, required=True)
    update.add_argument('--request-version', required=True)
    update.add_argument('--status', choices=REQUEST_STATES, required=True)
    update.add_argument('--by', choices=ROLES, required=True)
    update.add_argument('--summary', required=True)
    update.add_argument('--checks', default='')
    update.add_argument('--file', action='append', default=[])
    update.add_argument('--result-artifact')
    images = commands.add_parser('image', help='Prepare a selected region and preserve pixels outside it')
    image_ops = images.add_subparsers(dest='operation', required=True)
    for action in ('prepare', 'apply'):
        operation = image_ops.add_parser(action)
        operation.add_argument('artifact')
        operation.add_argument('note')
        operation.add_argument('--out', required=True)
        if action == 'apply':
            operation.add_argument('--edited', required=True)
            operation.add_argument('--request-version', required=True)
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
    encode.add_argument('--rev', type=int, help='Render an immutable saved draft rather than the live draft')
    script = commands.add_parser('script', help='Review and approve a narration draft')
    draft_ops = script.add_subparsers(dest='operation', required=True)
    draft_ops.add_parser('show').add_argument('id')
    approve = draft_ops.add_parser('approve')
    approve.add_argument('id')
    approve.add_argument('--revision', type=int, required=True)
    sync = commands.add_parser('sync', help='Match captions and picture to new narration')
    sync_ops = sync.add_subparsers(dest='operation', required=True)
    for action in ('plan', 'render'):
        operation = sync_ops.add_parser(action)
        operation.add_argument('id')
        operation.add_argument('--voice')
        operation.add_argument('--timings')
        operation.add_argument('--clips', help='Folder with 0001.wav, 0002.wav, ...')
        operation.add_argument('--effects', help='Sound effects already aligned to the new timeline')
        if action == 'render':
            operation.add_argument('--out', required=True)
            operation.add_argument('--font', default='sans-serif')
    transfer = commands.add_parser('handoff')
    sub = transfer.add_subparsers(dest='operation', required=True)
    queue = sub.add_parser('list')
    queue.add_argument('--to', choices=ROLES)
    queue.add_argument('--pending', action='store_true')
    queue.add_argument('--open', dest='open_only', action='store_true',
                       help='Include read and unread handoffs that have no reply')
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
        with project.lock():
            return install(project, args.agent, args.upgrade)
    if command == 'status':
        return server_status(project)
    if command == 'serve':
        return serve(project, args.port)
    if command == 'open':
        return open_workspace(project, args.id, args.port)
    if command == 'add':
        return project.add(vars(args))
    if command == 'list':
        return project.artifacts()
    if command == 'image':
        from images import prepare_image, apply_image
        if args.operation == 'prepare':
            return prepare_image(project, args.artifact, args.note, args.out)
        return apply_image(project, args.artifact, args.note, args.edited, args.out, args.request_version)
    if command == 'versions':
        if args.operation == 'list':
            return project.versions(args.id)
        if args.operation == 'create':
            return project.create_version(args.id)
        if args.operation == 'show':
            return project.version(args.id, args.rev)
        return project.publish_version(args.id, args.rev, args.video, args.summary, args.checks, args.by)
    if command == 'audio':
        return project.attach_audio(args.id, {field: getattr(args, field) for field in ('voice', 'music', 'effects')})
    if command == 'requests':
        if args.operation == 'list':
            return project.requests(args.artifact, args.status, args.open_only)
        return project.update_request(args.artifact, args.id,
                                      {'revision': args.revision, 'request_version': args.request_version,
                                       'status': args.status, 'by': args.by, 'summary': args.summary,
                                       'checks': args.checks, 'files': args.file, 'result_artifact': args.result_artifact})
    if command == 'render':
        return str(render(project, args.id, args.out, args.font, version=args.rev))
    if command == 'script':
        if args.operation == 'show':
            return draft_payload(project, args.id)
        _, _, original, _ = script_draft(project, args.id)
        return project.approve_script(args.id, args.revision, [cue['text'] for cue in original])
    if command == 'sync':
        inputs = dict(voice=args.voice, timings=args.timings, clips=args.clips, effects=args.effects)
        if args.operation == 'plan':
            return prepare(project, args.id, **inputs)[0]
        return render_synced(project, args.id, args.out, args.font, **inputs)
    if command in ('export-srt', 'review'):
        artifact = project.artifact(args.id)
        if command == 'review' and args.operation == 'show':
            return project.review(args.id)
        cues = load_cues(project, artifact)
        if command == 'export-srt':
            review = project.review(args.id)
            require_caption_export(review)
            out = destination(project, args.out)
            with out.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(format_srt(edited_cues(cues, review)))
            return str(out)
        source = sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8-sig')
        for field in artifact.get('fingerprints', {}):
            project.asset(artifact, field)
        return project.save_review(args.id, json.loads(source), len(cues))
    if args.operation == 'list':
        return project.handoffs(args.to, args.pending, open_only=args.open_only)
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
