"""Subtitle interchange and optional FFmpeg export."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

from model import Conflict, read_json, relative

STAMP = r'(?:\d+:)?\d{1,2}:\d{2}[,.]\d{3}'
ARROW = re.compile(rf'^\s*({STAMP})\s+-->\s+({STAMP})(?:\s+.*)?$')


def seconds(value):
    result = 0.0
    for piece in value.replace(',', '.').split(':'):
        result = result * 60 + float(piece)
    return result


def load_cues(project, artifact):
    if 'captions' not in artifact:
        return []
    return read_cues(project.asset(artifact, 'captions'), display=True)


def read_cues(path, *, display=False):
    if path.suffix.lower() == '.json':
        data = read_json(path)
        cues = data.get('captions') if isinstance(data, dict) else data
        if not isinstance(cues, list):
            raise ValueError('Timeline JSON must contain a captions array')
    else:
        cues = []
        for block in re.split(r'\n[ \t]*\n', path.read_text(encoding='utf-8-sig')):
            lines = block.strip().splitlines()
            for index, line in enumerate(lines):
                match = ARROW.fullmatch(line)
                if match:
                    cues.append({'start': seconds(match[1]), 'end': seconds(match[2]),
                                 'text': '\n'.join(lines[index + 1:])})
                    break
    result = []
    for cue in cues:
        start, end = float(cue['start']), float(cue['end'])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end:
            raise ValueError('Invalid caption timing')
        if not isinstance(cue['text'], str):
            raise ValueError('Caption text must be a string')
        if cue['text'].strip():
            if 'say_end' in cue:
                end = min(end, float(cue['say_end']) + (0.12 if display else 0))
            if end > start:
                result.append({'start': start, 'end': end, 'text': cue['text']})
    result.sort(key=lambda cue: cue['start'])
    for cue, following in zip(result, result[1:]):
        if cue['end'] > following['start']:
            raise ValueError('Overlapping captions are not supported. Split them before importing.')
    if not result:
        raise ValueError(f'No usable captions found in {path.name}')
    return result


def edited_cues(cues, review):
    return [dict(cue, text=review['captions'].get(str(idx), cue['text']))
            for idx, cue in enumerate(cues)]


def srt_stamp(time):
    millis = round(time * 1000)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    sec, ms = divmod(rest, 1000)
    return f'{hours:02}:{minutes:02}:{sec:02},{ms:03}'


def format_srt(cues):
    blocks = []
    for cue in cues:
        # Empty lines delimit cues in SRT; keep intentional text on one cue.
        words = '\n'.join(line for line in cue['text'].splitlines() if line.strip())
        if words:
            blocks.append(f"{len(blocks)+1}\n{srt_stamp(cue['start'])} --> {srt_stamp(cue['end'])}\n{words}")
    return '\n\n'.join(blocks) + ('\n' if blocks else '')


def destination(project, name):
    path = project.root / relative(name)
    if not path.parent.resolve().is_relative_to(project.root):
        raise ValueError('Output must stay inside the project')
    if path.exists() or path.is_symlink():
        raise Conflict(f'Output already exists: {name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def require_caption_export(review):
    if review.get('mode') == 'script' and review['captions']:
        raise Conflict('This draft changes narration. Approve the script, then run sync with new audio.')


def mix_audio(streams):
    filters = [f'[{source}]volume={level/100:.2f},apad[layer{i}]'
               for i, (source, level) in enumerate(streams)]
    labels = ''.join(f'[layer{i}]' for i in range(len(streams)))
    filters.append(f'{labels}amix=inputs={len(streams)}:duration=longest:normalize=0,'
                   'alimiter=limit=0.95:latency=1[a]')
    return ';'.join(filters)


def render(project, key, output, font, *, version=None):
    snapshot = project.version(key, version) if version is not None else None
    art = snapshot['source'] if snapshot else project.artifact(key)
    if art['kind'] != 'video':
        raise ValueError('Render is available only for video artifacts')
    if not output.lower().endswith('.mp4'):
        raise ValueError('Render output must end in .mp4')
    if not re.fullmatch(r'[\w -]{1,80}', font):
        raise ValueError('Invalid subtitle font family')
    out = destination(project, output)
    review = snapshot['review'] if snapshot else project.review(key)
    require_caption_export(review)
    video = project.asset(art, 'file')
    music = project.asset(art, 'music') if 'music' in art else None
    voice = project.asset(art, 'voice') if 'voice' in art else None
    effects = project.asset(art, 'effects') if 'effects' in art else None
    captions = format_srt(edited_cues(load_cues(project, art), review))
    channels = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                                        '-show_entries', 'stream=index', '-of', 'csv=p=0', str(video)],
                                       text=True, encoding='utf-8').strip()
    duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                              '-of', 'default=nw=1:nk=1', str(video)], text=True))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Cannot determine video duration')
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='.render-') as scratch:
        temp = Path(scratch) / 'result.mp4'
        cmd = ['ffmpeg', '-v', 'error', '-nostdin', '-i', str(video)]
        streams = [('0:a:0', review.get('voice', 100))] if channels and not voice else []
        input_index = 1
        for field, path in [('voice', voice), ('music', music), ('effects', effects)]:
            if path:
                cmd += ['-i', str(path)]
                streams.append((f'{input_index}:a:0', review.get(field, 100)))
                input_index += 1
        filters = []
        if art['mask']:
            filters.append(f"drawbox=x=0:y=ih*(100-{art['mask']})/100:w=iw:h=ih:color=0x080808:t=fill")
        if captions:
            (Path(scratch) / 'captions.srt').write_text(captions, encoding='utf-8')
            filters.append(f"subtitles=captions.srt:force_style='FontName={font},Outline=2,Shadow=1,MarginV=18'")
        cmd += ['-map', '0:v:0']
        if filters:
            cmd += ['-vf', ','.join(filters), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18']
        else:
            cmd += ['-c:v', 'copy']
        if streams:
            cmd += ['-filter_complex', mix_audio(streams), '-map', '[a]']
            cmd += ['-c:a', 'aac', '-b:a', '192k']
        cmd += ['-t', f'{duration:.6f}', '-movflags', '+faststart', str(temp)]
        subprocess.run(cmd, check=True, cwd=scratch)
        with project.lock():
            if out.exists() or out.is_symlink():
                raise Conflict(f'Output already exists: {output}')
            if snapshot is None and project.review(key)['revision'] != review['revision']:
                raise Conflict('Review changed while rendering. Render again from the latest revision.')
            temp.replace(out)
    return out
