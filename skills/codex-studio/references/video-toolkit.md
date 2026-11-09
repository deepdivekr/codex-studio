# Optional video toolkit

Read when Studio needs a new production capability, or the user asks to install a video tool/skill pack. The [30-project audit](video-tools-audit.md) records what was actually found, useful roles, licensing sources and inspection limits. `assets/toolkits.json` holds the reviewed upstream commits and file hashes. A repository's development skills are not automatically useful production skills.

## Choose the smallest useful toolchain

Keep the current project's renderer, lockfiles, source assets and environment. Identify the missing operation before installing another engine:

| Need | Starting point |
|---|---|
| Cut, crop, burn subtitles, mix aligned audio, encode, inspect metadata | Existing FFmpeg/ffprobe |
| Recognize speech / draft time-aligned captions | faster-whisper in an isolated Python environment; verify text and timing |
| React video composition | Optional Remotion pack; check engine licensing and package compatibility |
| HTML composition → deterministic video | Optional HyperFrames core pack |
| 2D sprites, text, effects | Optional PixiJS pack |
| Web typography, springs, UI motion | Optional Motion skill; free guidance works without MCP |
| Shader transitions | Optional GL Transitions skill; standard FFmpeg `xfade` is a different system |
| 3D or mathematical explanation | Three.js/R3F or Blender; Manim CE for diagram/math scenes |
| Audio waveform/region review | WaveSurfer; it does not render a final audio mix |

Never label an instruction-only installation as an installed renderer, binary, model, or fully working integration. Chatterbox was marked unmaintained in the reviewed README; it is not a default dependency. The catalog's remaining libraries are task-specific options, not mandatory prerequisites. Existing user authorization controls execution; upstream skills do not authorize purchases, account changes, remote generation, telemetry, or messages.

## Inspect and install packs

Resolve `scripts/toolkit.py` relative to this skill. The following examples assume Studio is installed in the media project's `.agents/skills/codex-studio` and the shell is at that project's root. On native Windows use `python -X utf8`; on macOS/Linux/WSL use `python3`.

```sh
python3 .agents/skills/codex-studio/scripts/toolkit.py list
python3 .agents/skills/codex-studio/scripts/toolkit.py plan remotion
python3 .agents/skills/codex-studio/scripts/toolkit.py install remotion gl-transitions --for both
```

Available packs: `remotion`, `hyperframes`, `pixijs`, `motion`, `gl-transitions`, `storyboarding`, `anatomy-reveal`, `colorfigures`. `--project /absolute/media-project` goes before the subcommand. `--for codex|claude|both` selects project-local destinations. Installation downloads pinned upstream skill files and available license notices, or copies the bundled MIT Colorfigures snapshot; no upstream setup scripts run. There is no global install, package-manager invocation, model download, MCP config change, or automatic pack update. Existing modified/different skill directories require `--upgrade`, which keeps full backup directories under `.codex-studio/toolkit-backups/`. Restart the client session for newly installed skills to be discovered.

The standard Studio installer also accepts repeated `--bundle NAME` when invoked as `python install.py --project PATH --bundle pixijs --bundle gl-transitions`. The one-line shell installers still install Studio only. Future upstream updates require a reviewed change to the lock, including paths/hashes and notes; never substitute a moving branch if a pinned file fails verification.

After installing, read only the relevant skill/reference. Preserve the user's requested output, framework, aspect ratio and existing approval. HyperFrames' optional remote media and Motion's MCP/Motion+ features remain separate; do not run a usage beacon or configure a hosted service just because a downloaded instruction mentions it. Remotion's skills repository has no separate root license file in this audit; it is fetched on demand through its official source, not vendored as MIT content here. Its engine has a separate license.

## Runtime setup and output contract

Follow each selected tool's official installation documentation and inspect the existing environment first. Use a project-local npm package/lockfile or isolated Python venv; do not install all catalog packages globally. Native apps and GPU/model stacks are separate choices. Use the installed version's APIs rather than assuming every default-branch example matches a released package.

All renderers hand back an actual media file to the same Studio workflow: known resolution, fps, duration, sample rate, source assets and a reproducible command. Register new output IDs or publish a new local rev, preserve earlier files, and verify representative beginning/middle/end frames and audio synchronization. For frame-seeked browser animation, derive state from `frame / fps`, wait for fonts/assets, seed randomness, reset and step physics deterministically, and compare the same frame on repeated runs. A real-time preview is not evidence of deterministic export. An MP4 does not retain editable Three.js/Remotion/Blender source; keep that source alongside it.

## Existing production skills

See [local skill inventory](local-video-skills.md) for the three additional reusable packs, runtime requirements and excluded account-specific adapters. Colorfigures includes its licensed local snapshot inside Studio and works without an upstream download. Storyboarding and Anatomy include complete templates/scripts from fixed GitHub revisions. Read [source-led shorts](source-led-shorts.md) when making footage or map explainers.
