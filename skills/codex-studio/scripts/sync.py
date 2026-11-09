"""Align existing picture to approved narration using measured cue boundaries."""
from bisect import bisect_right
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import tempfile
import wave

from media import destination, edited_cues, format_srt, load_cues, read_cues
from model import Conflict, read_json, relative


def script_draft(project, key):
    artifact = project.artifact(key)
    review = project.review(key)
    original = load_cues(project, artifact)
    if not original:
        raise ValueError('Register subtitles before revising narration')
    edited = edited_cues(original, review)
    return artifact, review, original, edited


def draft_payload(project, key):
    _, review, before, after = script_draft(project, key)
    return {'artifact': key, 'revision': review['revision'], 'approved': review.get('script_approved'),
            'cues': [{'id': index, 'text': new['text'], 'previous': old['text'],
                      'start': old['start'], 'end': old['end']}
                     for index, (old, new) in enumerate(zip(before, after), 1)]}


def probe(path, stream):
    result = subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', stream, '-show_entries',
         'stream=duration,avg_frame_rate:format=duration', '-of', 'json', str(path)], encoding='utf-8')
    data = json.loads(result)
    if not data['streams']:
        raise ValueError(f'{path.name}: missing {stream} stream')
    return float(data['streams'][0].get('duration') or data['format']['duration'])


def wav_info(path):
    with wave.open(str(path), 'rb') as source:
        layout = (source.getnchannels(), source.getsampwidth(), source.getframerate())
        return layout, source.getnframes()


def clips_timing(project, folder, original, edited, old_duration):
    folder = relative(folder)
    paths, spans, gap_frames = [], [], []
    cursor = 0
    layout = None
    previous = 0
    for index, (old, new) in enumerate(zip(original, edited), 1):
        path = project.local(f'{folder}/{index:04}.wav')
        fmt, frames = wav_info(path)
        if fmt[1] != 2 or frames <= 0 or (layout and fmt != layout):
            raise ValueError('Cue WAV files must be nonempty 16-bit PCM with the same rate and channels')
        layout = fmt
        gap = round(max(0, old['start'] - previous) * fmt[2])
        gap_frames.append(gap)
        cursor += gap
        spans.append({'start': cursor / fmt[2], 'end': (cursor + frames) / fmt[2], 'text': new['text']})
        cursor += frames
        paths.append(path)
        previous = old['end']
    tail = round(max(0, old_duration - previous) * layout[2])
    return spans, (cursor + tail) / layout[2], (layout, paths, gap_frames, tail)


def write_clips(output, bundle):
    layout, paths, gaps, tail = bundle
    with wave.open(str(output), 'wb') as out:
        out.setnchannels(layout[0])
        out.setsampwidth(layout[1])
        out.setframerate(layout[2])
        for path, gap in zip(paths, gaps):
            out.writeframesraw(bytes(gap * layout[0] * layout[1]))
            with wave.open(str(path), 'rb') as source:
                remaining = source.getnframes()
                while remaining:
                    block = min(remaining, 65536)
                    out.writeframesraw(source.readframes(block))
                    remaining -= block
        out.writeframesraw(bytes(tail * layout[0] * layout[1]))


def picture_map(original, aligned, old_duration, duration, fps):
    frame = 1 / fps
    points = [(0.0, 0.0)]
    for index, (old, new) in enumerate(zip(original, aligned)):
        if old['start'] > 0.00001:
            if new['start'] <= points[-1][1]:
                raise ValueError(f'Cue {index + 1}: new audio leaves no room for the preceding picture')
            points.append((old['start'], new['start']))
        if index + 1 < len(original):
            old_next, new_next = original[index + 1]['start'], aligned[index + 1]['start']
            if (old_next - old['end'] >= frame and new_next - new['end'] >= frame
                    and old['end'] > points[-1][0] and new['end'] > points[-1][1]):
                points.append((old['end'], new['end']))
        elif (old_duration - old['end'] >= frame and duration - new['end'] >= frame
              and old['end'] > points[-1][0] and new['end'] > points[-1][1]):
            points.append((old['end'], new['end']))
    if old_duration <= points[-1][0] or duration <= points[-1][1]:
        raise ValueError('Narration or original video ends before the last picture boundary')
    points.append((old_duration, duration))
    return points


def retimed(points, value):
    idx = min(len(points) - 2, max(0, bisect_right([p[0] for p in points], value) - 1))
    old, new = points[idx]
    end, target = points[idx + 1]
    return new + (value - old) * (target - new) / (end - old)


def title_checks(project, artifact, points, aligned):
    if not artifact['captions'].lower().endswith('.json'):
        return 0
    timeline = read_json(project.asset(artifact, 'captions'))
    if not isinstance(timeline, dict) or not timeline.get('shots'):
        return 0
    count = 0
    for card in timeline['captions']:
        if card['text'] or not timeline['shots'][card['shot']].startswith('card:'):
            continue
        start = retimed(points, card['start'])
        end = retimed(points, card['end'])
        overlaps = any(cue['start'] < end - 0.025 and cue['end'] > start + 0.025 for cue in aligned)
        if overlaps or end - start < min(.75, card['end'] - card['start']) - .025:
            raise ValueError(f"Title at {card['start']:.2f}s needs a quiet gap in the new narration. "
                             "Keep the chapter pause or supply per-cue WAV files.")
        count += 1
    return count


def prepare(project, key, *, voice=None, timings=None, clips=None, effects=None):
    artifact, review, original, edited = script_draft(project, key)
    if review.get('mode') != 'script' or not review.get('script_approved'):
        raise Conflict('Review and approve the saved narration draft first')
    picture = project.asset(artifact, 'file')
    old_duration = probe(picture, 'v:0')
    fps = float(Fraction(artifact['fps']))
    if original[-1]['end'] > old_duration + 1 / fps:
        raise ValueError('Original subtitles extend beyond the picture')
    music = project.asset(artifact, 'music') if artifact.get('music') else None
    new_effects = project.local(effects) if effects else None
    bundle = None
    if clips and not (voice or timings):
        aligned, duration, bundle = clips_timing(project, clips, original, edited, old_duration)
        source = None
    elif voice and timings and not clips:
        source = project.local(voice)
        duration = probe(source, 'a:0')
        aligned = read_cues(project.local(timings))
        if len(aligned) != len(edited):
            raise ValueError('The new alignment must contain one cue per approved line, in order')
        for index, (cue, expected) in enumerate(zip(aligned, edited), 1):
            if ' '.join(cue['text'].split()) != ' '.join(expected['text'].split()):
                raise ValueError(f'Cue {index}: aligned words do not match the approved script')
        if aligned[-1]['end'] > duration + 0.025:
            raise ValueError('New caption timing extends beyond the narration')
    else:
        raise ValueError('Supply --voice with --timings, or supply --clips')
    points = picture_map(original, aligned, old_duration, duration, fps)
    cards = title_checks(project, artifact, points, aligned)
    rates = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(points, points[1:])]
    stats = {'artifact': key, 'revision': review['revision'], 'original_seconds': round(old_duration, 3),
             'effects_need_alignment': bool(artifact.get('effects') and not new_effects),
             'new_seconds': round(duration, 3), 'preserved_title_cards': cards,
             'min_picture_duration_ratio': round(min(rates), 3), 'max_picture_duration_ratio': round(max(rates), 3),
             'cue_starts': [{'id': i, 'before': old['start'], 'after': new['start']}
                            for i, (old, new) in enumerate(zip(original, aligned), 1)]}
    return stats, (artifact, review, picture, source, music, bundle, aligned, points, duration, new_effects)


def pts_expression(points):
    # A balanced expression keeps FFmpeg's evaluation depth small for long videos.
    if len(points) == 2:
        (old, new), (end, target) = points
        ratio = (target - new) / (end - old)
        return f'({new:.10f}+(T-{old:.10f})*{ratio:.12f})/TB'
    mid = len(points) // 2
    return f'if(lt(T,{points[mid][0]:.10f}),{pts_expression(points[:mid+1])},{pts_expression(points[mid:])})'


def render_synced(project, key, output, font, **inputs):
    from media import mix_audio
    stats, (art, review, picture, source, music, bundle, aligned, points, duration, effects) = prepare(project, key, **inputs)
    if stats['effects_need_alignment']:
        raise ValueError('Recreate sound effects on the new timeline and pass --effects NEW_AUDIO')
    if not output.lower().endswith('.mp4') or not re.fullmatch(r'[\w -]{1,80}', font):
        raise ValueError('Choose an MP4 output and a valid font family')
    out = destination(project, output)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='.sync-') as scratch:
        scratch = Path(scratch)
        if bundle:
            source = scratch / 'narration.wav'
            write_clips(source, bundle)
        (scratch / 'captions.srt').write_text(format_srt(aligned), encoding='utf-8')
        filters = ['setpts=PTS-STARTPTS', 'settb=AVTB', f"setpts='{pts_expression(points)}'",
                   f"fps={art['fps']}:start_time=0:round=up", 'tpad=stop_mode=clone:stop_duration=1']
        if art['mask']:
            filters.append(f"drawbox=x=0:y=ih*(100-{art['mask']})/100:w=iw:h=ih:color=0x080808:t=fill")
        filters.append(f"subtitles=captions.srt:force_style='FontName={font},Outline=2,Shadow=1,MarginV=18'")
        (scratch / 'video-filter.txt').write_text(','.join(filters), encoding='utf-8')
        temp = scratch / 'synced.mp4'
        cmd = ['ffmpeg', '-v', 'error', '-nostdin', '-i', str(picture), '-i', str(source)]
        streams = [('1:a:0', review.get('voice', 100))]
        if music:
            cmd += ['-stream_loop', '-1', '-i', str(music)]
            streams.append(('2:a:0', review['music']))
        if effects:
            cmd += ['-i', str(effects)]
            streams.append((f'{3 if music else 2}:a:0', review.get('effects', 100)))
        # Keep long graphs in a file (Windows has a command-line length limit).
        # FFmpeg 9 removed filter_script; older releases lack the /option syntax.
        help_text = subprocess.run(['ffmpeg', '-hide_banner', '-h', 'full'],
                                   check=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace').stdout
        filter_option = '-filter_script:v' if '-filter_script' in help_text else '-/filter:v'
        cmd += ['-map', '0:v:0', filter_option, 'video-filter.txt', '-c:v', 'libx264',
                '-preset', 'veryfast', '-crf', '18']
        cmd += ['-filter_complex', mix_audio(streams), '-map', '[a]']
        cmd += ['-t', f'{duration:.6f}', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(temp)]
        subprocess.run(cmd, check=True, cwd=scratch)
        for stream, tolerance in [('v:0', 2 / float(Fraction(art['fps']))), ('a:0', .08)]:
            if abs(probe(temp, stream) - duration) > tolerance:
                raise ValueError(f'Output {stream} duration does not match the new narration')
        with project.lock():
            if out.exists() or out.is_symlink() or project.review(key)['revision'] != review['revision']:
                raise Conflict('Output already exists or review changed during rendering')
            temp.replace(out)
    return dict(stats, output=str(out))
