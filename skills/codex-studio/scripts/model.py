"""Project-local records shared by the CLI and web interface."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import uuid

VERSION = 1
ROLES = ('codex', 'claude', 'human')
REQUEST_STATES = ('pending', 'in_progress', 'done', 'blocked')
KEY = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
HANDOFF_KEY = re.compile(r'[a-f0-9]{32}\Z')


class Conflict(ValueError):
    pass


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        handle.write((json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def git(root, *args):
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, encoding='utf-8', check=True, timeout=5)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def project_root(explicit):
    if explicit is not None:
        path = Path(explicit).resolve(strict=True)
        if not path.is_dir():
            raise ValueError('--project must be a directory')
        return path
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / '.codex-artifacts').is_dir() or (candidate / '.git').exists():
            return candidate
    raise ValueError('Run inside a Git checkout or pass --project PATH')


def relative(value):
    if not isinstance(value, str) or not value.strip() or '\\' in value or ':' in value:
        raise ValueError('Use a project-relative path with / separators')
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('Path must stay inside the project')
    return path.as_posix()


def required_text(value, label, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{label}: enter 1–{limit} characters')
    return value.strip()


def optional_text(value, label, limit):
    return '' if value is None or value == '' else required_text(value, label, limit)


def fps_value(value):
    try:
        rate = Fraction(str(value)).limit_denominator(100_000)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("Use a frame rate such as 30 or 30000/1001") from error
    if not 1 <= rate <= 240:
        raise ValueError('Frame rate must be between 1 and 240')
    return str(rate)


@lru_cache(maxsize=128)
def _fingerprint(path, size, mtime_ns):
    digest = sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path):
    stat = path.stat()
    return _fingerprint(path, stat.st_size, stat.st_mtime_ns)


def image_selection(value, artifact):
    if not isinstance(value, dict) or artifact['kind'] != 'image':
        raise ValueError('Selections are only available for images')
    kind = value.get('kind')
    fields = ('x', 'y', 'width', 'height') if kind == 'rect' else ('x', 'y')
    if kind not in ('point', 'rect'):
        raise ValueError('Use a point or rectangular image selection')
    clean = {'kind': kind}
    for field in fields:
        number = value.get(field)
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError('Selection coordinates must be finite numbers from 0 to 1')
        clean[field] = number
    if kind == 'rect' and (clean['width'] <= 0 or clean['height'] <= 0
                           or clean['x'] + clean['width'] > 1 + 1e-9
                           or clean['y'] + clean['height'] > 1 + 1e-9):
        raise ValueError('Selected rectangle must fit inside the image')
    for field in ('image_width', 'image_height'):
        number = value.get(field)
        if type(number) is not int or not 1 <= number <= 100_000:
            raise ValueError('Selection must include the original image dimensions')
        clean[field] = number
    source = value.get('source_sha256')
    if not isinstance(source, str) or not re.fullmatch('[a-f0-9]{64}', source):
        raise ValueError('Selection must identify its source image')
    if source != artifact.get('fingerprints', {}).get('file'):
        raise Conflict('The selected image changed. Reopen the current image before selecting it.')
    clean['source_sha256'] = source
    return clean


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.data = self.root / '.codex-artifacts'
        if self.data.resolve().parent != self.root or self.data.is_symlink():
            raise ValueError('Project records directory must be local to this project')

    def local(self, name):
        clean = relative(name)
        resolved = (self.root / clean).resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError(f'Cannot open a file outside the project: {clean}')
        return resolved

    def storage(self, *parts):
        path = self.data.joinpath(*parts)
        resolved = path.resolve()
        # A concurrently locked file can retain Win32's extended-length prefix
        # in Python 3.10 even when its parent resolved without that prefix.
        if os.name == 'nt':
            value = str(resolved)
            if value.startswith('\\\\?\\UNC\\'):
                resolved = Path('\\\\' + value[8:])
            elif value.startswith('\\\\?\\') and re.match(r'[A-Za-z]:\\', value[4:]):
                resolved = Path(value[4:])
        if not resolved.is_relative_to(self.data):
            raise ValueError(f'Project record resolves outside the records directory: {resolved} (expected {self.data})')
        return path

    def init(self):
        self.data.mkdir(exist_ok=True)
        gitignore = self.storage('.gitignore')
        if not gitignore.exists():
            try:
                with gitignore.open('x', encoding='utf-8') as handle:
                    handle.write('# Runtime only\n.lock\nruntime/\n*.tmp\n')
            except FileExistsError:
                pass

    @contextmanager
    def lock(self, name='.lock', blocking=True):
        self.init()
        path = self.storage(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a+b') as handle:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                try:
                    msvcrt.locking(handle.fileno(), mode, 1)
                except OSError as error:
                    if blocking:
                        raise
                    raise Conflict("An artifact server is already running or starting") from error
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                mode = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
                try:
                    fcntl.flock(handle, mode)
                except BlockingIOError as error:
                    raise Conflict("An artifact server is already running or starting") from error
                try:
                    yield
                finally:
                    fcntl.flock(handle, fcntl.LOCK_UN)

    def add(self, spec):
        key = spec['id']
        if not KEY.fullmatch(key):
            raise ValueError('Use a lowercase artifact ID with letters, digits and hyphens')
        kind = spec['kind']
        source = relative(spec['file'])
        original = self.local(source)
        extensions = {'video': {'.mp4', '.webm'}, 'html': {'.html', '.htm'},
                      'image': {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'}}
        if original.suffix.lower() not in extensions[kind]:
            raise ValueError(f'Unsupported {kind} file: {original.suffix}')
        record = {'version': VERSION, 'id': key, 'kind': kind,
                  'title': required_text(spec['title'], 'Title', 140), 'file': source}
        if kind == 'video':
            rate = spec['fps']
            if rate is None:
                try:
                    rate = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                                   '-show_entries', 'stream=avg_frame_rate', '-of', 'csv=p=0',
                                                   str(original)], text=True, timeout=15).strip()
                except (OSError, subprocess.SubprocessError) as error:
                    raise ValueError('Set --fps explicitly or install ffprobe') from error
            record.update(fps=fps_value(rate), mask=spec['mask'], music_level=spec['music_level'])
            if not 0 <= record['mask'] <= 45 or not 0 <= record['music_level'] <= 100:
                raise ValueError('Caption mask: 0–45%; music level: 0–100%')
            record['fingerprints'] = {'file': fingerprint(original)}
            for field in ('captions', 'music', 'voice', 'effects'):
                if spec.get(field):
                    value = relative(spec[field])
                    asset = self.local(value)
                    if field == 'captions' and asset.suffix.lower() not in ('.srt', '.vtt', '.json'):
                        raise ValueError('Use SRT, WebVTT or a timeline JSON for captions')
                    if field in ('music', 'voice', 'effects') and asset.suffix.lower() not in ('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.opus', '.flac'):
                        raise ValueError(f'Unsupported audio file: {asset.suffix}')
                    record[field] = value
                    record['fingerprints'][field] = fingerprint(asset)
        elif kind == 'image':
            record['fingerprints'] = {'file': fingerprint(original)}
        elif kind == 'html':
            root = PurePosixPath(source).parent
            assets = []
            for item in spec.get('asset', []):
                value = relative(item)
                asset = self.local(value)
                if not PurePosixPath(value).is_relative_to(root) or asset.suffix.lower() not in {
                    '.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.avif',
                    '.woff', '.woff2', '.mp4', '.webm', '.mp3', '.wav', '.ogg', '.json'
                }:
                    raise ValueError('HTML assets must be supported files beside or below the HTML entry')
                assets.append(value)
            record['assets'] = sorted(set(assets))
        with self.lock():
            target = self.storage('artifacts', key + '.json')
            if target.exists():
                raise Conflict(f'Artifact already exists: {key}. Choose a new ID for a new revision.')
            write_json(target, record)
        return record

    def artifacts(self):
        return [self.artifact(path.stem) for path in sorted(self.storage('artifacts').glob('*.json'))]

    def artifact(self, key):
        if not KEY.fullmatch(key):
            raise ValueError('Invalid artifact ID')
        record = read_json(self.storage('artifacts', key + '.json'))
        if record.get('version') != VERSION or record.get('id') != key:
            raise ValueError('Artifact record version or ID mismatch')
        # Older image registrations had no hash. Bind new selections to the file
        # presented now; saved selections retain their own immutable source hash.
        if record['kind'] == 'image' and not record.get('fingerprints'):
            record['fingerprints'] = {'file': fingerprint(self.local(record['file']))}
        return record

    def asset(self, artifact, field):
        path = self.local(artifact[field])
        expected = artifact.get('fingerprints', {}).get(field)
        if expected and fingerprint(path) != expected:
            raise Conflict(f'{field} changed on disk. Register the new media under a new artifact ID.')
        return path

    def review(self, key):
        artifact = self.artifact(key)
        path = self.storage('reviews', key + '.json')
        if path.exists():
            record = read_json(path)
            if record.get('version') != VERSION:
                raise ValueError('Unsupported review version')
            record.setdefault('voice', 100)
            record.setdefault('effects', 100)
            return record
        return {'version': VERSION, 'revision': 0, 'music': artifact.get('music_level', 100),
                'voice': 100, 'effects': 100, 'notes': [], 'captions': {}, 'mode': 'caption'}

    def save_review(self, key, change, cue_count):
        artifact = self.artifact(key)
        if not isinstance(change, dict):
            raise ValueError('Review must be an object')
        rev, music = change.get('revision'), change.get('music')
        levels = {field: change.get(field, 100) for field in ('voice', 'effects')}
        if any(type(value) is not int or not 0 <= value <= 100 for value in levels.values()):
            raise ValueError('Audio levels must be integers from 0 to 100')
        mode = change.get('mode', 'caption')
        if mode not in ('caption', 'script') or (mode == 'script' and artifact['kind'] != 'video'):
            raise ValueError('Narration edits are only available for video')
        notes, captions = change.get('notes'), change.get('captions')
        if type(rev) is not int or type(music) is not int or not 0 <= music <= 100:
            raise ValueError('Invalid review revision or volume')
        if not isinstance(notes, list) or len(notes) > 500 or not isinstance(captions, dict):
            raise ValueError('Invalid notes or captions')
        cleaned = []
        seen = set()
        for note in notes:
            if not isinstance(note, dict):
                raise ValueError('Invalid note')
            ident, frame, author = note.get('id'), note.get('frame'), note.get('author')
            if not isinstance(ident, str) or not KEY.fullmatch(ident) or ident in seen or author not in ROLES:
                raise ValueError('Invalid or duplicate note ID or author')
            if artifact['kind'] == 'video':
                if type(frame) is not int or not 0 <= frame <= 20_000_000:
                    raise ValueError('Invalid frame index')
            elif frame is not None:
                raise ValueError('Only video notes may have a frame')
            seen.add(ident)
            cleaned.append({'id': ident, 'frame': frame, 'author': author,
                            'text': required_text(note.get('text'), 'Note', 2000)})
            if note.get('selection') is not None:
                cleaned[-1]['selection'] = image_selection(note['selection'], artifact)
        for idx, value in captions.items():
            if (not re.fullmatch(r'0|[1-9][0-9]{0,6}', idx) or int(idx) >= cue_count
                    or not isinstance(value, str) or len(value) > 1000):
                raise ValueError('Invalid caption edit')
        with self.lock():
            previous = self.review(key)
            if artifact['kind'] == 'image':
                self.asset(artifact, 'file')
            if previous['revision'] != rev:
                raise Conflict('Another session saved changes. Copy your draft before reloading.')
            record = {'version': VERSION, 'revision': rev + 1, 'updated_at': now(), 'music': music,
                      'notes': cleaned, 'captions': captions, 'mode': mode, **levels}
            if mode == 'script' and previous.get('mode') == mode and previous['captions'] == captions:
                if previous.get('script_approved'):
                    record['script_approved'] = previous['script_approved']
            if artifact['kind'] == 'video':
                self._snapshot_version(key, artifact, record)
            write_json(self.storage('reviews', key + '.json'), record)
        return record

    def versions(self, key):
        self.artifact(key)
        rows = [read_json(path) for path in self.storage('versions', key).glob('rev-*.json')]
        return sorted(rows, key=lambda item: item['rev'], reverse=True)

    def version(self, key, rev):
        self.artifact(key)
        if type(rev) is not int or rev < 1:
            raise ValueError('Invalid version number')
        return read_json(self.storage('versions', key, f'rev-{rev}.json'))

    def _snapshot_version(self, key, artifact, review):
        rev = max((item['rev'] for item in self.versions(key)), default=0) + 1
        review['saved_rev'] = rev
        row = {'version': VERSION, 'rev': rev, 'artifact': key, 'title': artifact['title'],
               'created_at': now(), 'state': 'pending', 'source': artifact, 'review': review,
               'summary': '', 'checks': '', 'request_results': []}
        write_json(self.storage('versions', key, f'rev-{rev}.json'), row)
        return row

    def create_version(self, key):
        with self.lock():
            art = self.artifact(key)
            if art['kind'] != 'video':
                raise ValueError('Video versions require a video artifact')
            review = self.review(key)
            review.update(revision=review['revision'] + 1, updated_at=now())
            row = self._snapshot_version(key, art, review)
            write_json(self.storage('reviews', key + '.json'), review)
            return row

    def publish_version(self, key, rev, video, summary, checks, actor):
        if actor not in ('codex', 'claude'):
            raise ValueError('Record the client that produced the video')
        summary = required_text(summary, 'Version summary', 6000)
        checks = required_text(checks, 'Verification', 6000)
        source = self.local(video)
        if source.suffix.lower() != '.mp4':
            raise ValueError('Version output must be an MP4')
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                                  '-show_entries', 'stream=codec_type', '-of', 'json', str(source)],
                                                 text=True, timeout=15))
        if not info.get('streams'):
            raise ValueError('The MP4 has no video stream')
        with self.lock():
            row = self.version(key, rev)
            if row['state'] == 'ready':
                raise Conflict('This version is complete and immutable. Create a new version instead.')
            target = self.storage('versions', key, f'rev-{rev}.mp4')
            if target.exists():
                raise Conflict('A preserved output already exists for this version')
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temp = Path(handle.name)
            try:
                before = source.stat()
                shutil.copyfile(source, temp)
                after = source.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise Conflict('The video changed while preserving the version')
                digest = fingerprint(temp)
                if digest != fingerprint(source):
                    raise Conflict('The preserved video does not match its source')
                results = []
                for note in row['review']['notes']:
                    try:
                        item = self.request_item(key, note['id'])
                        if any(item.get(field) != note.get(field) for field in ('frame', 'text', 'author')):
                            raise FileNotFoundError()
                    except FileNotFoundError:
                        item = dict(note, status='pending', summary='', checks='')
                    results.append(item)
                temp.replace(target)
                row.update(state='ready', completed_at=now(), by=actor, summary=summary, checks=checks,
                           video=target.relative_to(self.root).as_posix(), sha256=digest,
                           bytes=target.stat().st_size, request_results=results)
                write_json(self.storage('versions', key, f'rev-{rev}.json'), row)
            finally:
                temp.unlink(missing_ok=True)
            return row

    def version_video(self, key, rev):
        row = self.version(key, rev)
        if row['state'] != 'ready':
            raise FileNotFoundError('This version has no completed video yet')
        path = self.local(row['video'])
        if fingerprint(path) != row['sha256']:
            raise Conflict('The preserved version video changed on disk')
        return path

    def attach_audio(self, key, tracks):
        with self.lock():
            art = self.artifact(key)
            if art['kind'] != 'video':
                raise ValueError('Audio layers require a video artifact')
            self.asset(art, 'file')
            updates = {}
            for field, value in tracks.items():
                if value is None:
                    continue
                if field not in ('voice', 'music', 'effects'):
                    raise ValueError('Unknown audio layer')
                source = self.local(value)
                if source.suffix.lower() not in ('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.opus', '.flac'):
                    raise ValueError('Unsupported audio file')
                updates[field] = (relative(value), fingerprint(source))
            if not updates:
                raise ValueError('Provide at least one audio layer')
            if all(art.get(field) == value and art.get('fingerprints', {}).get(field) == digest
                   for field, (value, digest) in updates.items()):
                return art
            review = self.review(key)
            # Preserve originals and reject drafts/renders based on the former audio setup.
            write_json(self.storage('audio-history', key, uuid.uuid4().hex + '.json'),
                       {'at': now(), 'artifact': art, 'review': review})
            review.update(revision=review['revision'] + 1, updated_at=now())
            write_json(self.storage('reviews', key + '.json'), review)
            for field, (value, digest) in updates.items():
                art[field] = value
                art.setdefault('fingerprints', {})[field] = digest
            write_json(self.storage('artifacts', key + '.json'), art)
            return art

    def request_item(self, key, ident, *, art=None, review=None):
        if not isinstance(ident, str) or not KEY.fullmatch(ident):
            raise ValueError('Invalid request ID')
        art = art or self.artifact(key)
        review = review or self.review(key)
        note = next((item for item in review['notes'] if item['id'] == ident), None)
        if note is None:
            raise FileNotFoundError('Saved request not found')
        version = sha256(json.dumps([note, art.get('fingerprints', {}).get('file', art['file'])],
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = self.storage('requests', key, ident + '.json')
        stored = read_json(path) if path.exists() else {'revision': 0, 'history': []}
        current = stored if stored.get('request_version') == version else {}
        return {**note, 'artifact': key, 'title': art['title'], 'kind': art['kind'],
                'fps': art.get('fps'), 'file': art['file'],
                'source_version': art.get('fingerprints', {}).get('file', art['file']),
                'request_version': version, 'review_revision': review['revision'],
                'revision': stored['revision'], 'status': current.get('status', 'pending'),
                'by': current.get('by'), 'summary': current.get('summary', ''),
                'checks': current.get('checks', ''), 'files': current.get('files', []),
                'result_artifact': current.get('result_artifact'), 'updated_at': current.get('at'),
                'history': stored['history']}

    def requests(self, key=None, state=None, open_only=False):
        if state is not None and state not in REQUEST_STATES:
            raise ValueError('Invalid request status')
        rows = []
        for art in [self.artifact(key)] if key else self.artifacts():
            review = self.review(art['id'])
            for note in sorted(review['notes'], key=lambda item: (item['frame'] or 0, item['id'])):
                item = self.request_item(art['id'], note['id'], art=art, review=review)
                if (state is None or item['status'] == state) and (not open_only or item['status'] != 'done'):
                    rows.append(item)
        return rows

    def update_request(self, key, ident, body):
        state, actor = body.get('status'), body.get('by')
        if state not in REQUEST_STATES or actor not in ROLES:
            raise ValueError('Invalid request status or author')
        summary = required_text(body.get('summary'), 'Result', 4000)
        checks = (required_text if state == 'done' else optional_text)(body.get('checks'), 'Verification', 4000)
        files = body.get('files', [])
        if not isinstance(files, list) or len(files) > 100:
            raise ValueError('Provide at most 100 result files')
        files = list(dict.fromkeys(relative(name) for name in files))
        for name in files:
            self.local(name)
        result = body.get('result_artifact') or None
        if result:
            self.artifact(result)
        with self.lock():
            item = self.request_item(key, ident)
            if (type(body.get('revision')) is not int or body['revision'] != item['revision']
                    or body.get('request_version') != item['request_version']):
                raise Conflict('The request or its status changed. Read it again before updating.')
            if state == 'done':
                art = self.artifact(key)
                self.asset(art, 'file')
                if item.get('selection'):
                    image_selection(item['selection'], art)
            entry = {'at': now(), 'status': state, 'by': actor, 'summary': summary, 'checks': checks,
                     'files': files, 'result_artifact': result, 'request_version': item['request_version'],
                     'request_text': item['text'], 'frame': item['frame']}
            if item.get('selection'):
                entry['selection'] = item['selection']
            write_json(self.storage('requests', key, ident + '.json'),
                       {'version': VERSION, 'revision': item['revision'] + 1, **entry,
                        'history': [*item['history'], entry]})
            return self.request_item(key, ident)

    def approve_script(self, key, revision, originals):
        with self.lock():
            review = self.review(key)
            if type(revision) is not int or review["revision"] != revision:
                raise Conflict("The draft changed. Reopen it before approving the script.")
            if review.get("mode") != "script" or not any(
                text != originals[int(idx)] for idx, text in review["captions"].items()
            ):
                raise ValueError("Save at least one narration edit before approval")
            if any(not text.strip() for text in review["captions"].values()):
                raise ValueError("Deleting an entire spoken cue requires an explicit timeline edit")
            if not review.get("script_approved"):
                review.update(revision=revision + 1, updated_at=now(), script_approved=now())
                write_json(self.storage("reviews", key + ".json"), review)
        return review

    def handoff(self, ident):
        if not isinstance(ident, str) or not HANDOFF_KEY.fullmatch(ident):
            raise ValueError('Invalid handoff ID')
        item = read_json(self.storage('handoffs', ident + '.json'))
        if item.get('version') != VERSION or item.get('id') != ident:
            raise ValueError('Handoff record version or ID mismatch')
        ack = self.storage('acks', ident + '.json')
        return dict(item, acknowledgment=read_json(ack) if ack.exists() else None)

    def handoffs(self, recipient=None, pending=False, *, open_only=False):
        items = [self.handoff(path.stem) for path in self.storage('handoffs').glob('*.json')]
        replied = {item['reply_to'] for item in items if item.get('reply_to')} if open_only else set()
        return sorted((item for item in items
                       if (recipient is None or item['to'] == recipient)
                       and item['id'] not in replied
                       and (not pending or not item['acknowledgment'])),
                      key=lambda item: (item['created_at'], item['id']), reverse=True)

    def create_handoff(self, body):
        if not isinstance(body, dict):
            raise ValueError('Handoff must be an object')
        sender, receiver = body.get('from'), body.get('to')
        if sender not in ROLES or receiver not in ROLES or sender == receiver:
            raise ValueError('Pick different sender and recipient roles')
        refs = body.get('files', [])
        if not isinstance(refs, list) or len(refs) > 100:
            raise ValueError('Provide at most 100 project-relative file paths')
        files = list(dict.fromkeys(relative(ref) for ref in refs))
        reply = body.get('reply_to') or None
        if reply:
            previous = self.handoff(reply)
            if (previous['to'], previous['from']) != (sender, receiver):
                raise ValueError('Reply must return to the previous sender')
        artifact = body.get('artifact') or None
        review = self.review(artifact) if artifact else None
        item = {'version': VERSION, 'id': uuid.uuid4().hex, 'created_at': now(),
                'from': sender, 'to': receiver, 'reply_to': reply, 'artifact': artifact,
                'review_revision': review['revision'] if review else None,
                'branch': git(self.root, 'branch', '--show-current'), 'commit': git(self.root, 'rev-parse', 'HEAD'),
                'title': required_text(body.get('title'), 'Title', 140),
                'summary': required_text(body.get('summary'), 'Summary', 10000),
                'next': required_text(body.get('next'), 'Next step', 10000),
                'checks': optional_text(body.get('checks'), 'Verification', 6000),
                'files': files}
        with self.lock():
            write_json(self.storage('handoffs', item['id'] + '.json'), item)
        return dict(item, acknowledgment=None)

    def acknowledge(self, ident, role):
        with self.lock():
            item = self.handoff(ident)
            if role != item['to']:
                raise ValueError('Only the addressed recipient can acknowledge this handoff')
            ack = item['acknowledgment']
            if ack is None:
                ack = {'version': VERSION, 'handoff': ident, 'by': role, 'at': now()}
                write_json(self.storage('acks', ident + '.json'), ack)
        return ack
