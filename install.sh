#!/usr/bin/env bash
# Install or update Codex Studio in the current project.
set -euo pipefail

studio_python=''
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    studio_python="$(command -v "$candidate")"
    break
  fi
done
if [ -z "$studio_python" ]; then
  echo 'Codex Studio needs Python 3.10 or newer. Install Python, then run this command again.' >&2
  exit 1
fi

studio_temp="$(mktemp -d)"
trap 'rm -f -- "$studio_temp/install.py"; rmdir -- "$studio_temp"' EXIT
curl -fsSL https://raw.githubusercontent.com/deepdivekr/codex-studio/refs/heads/main/install.py -o "$studio_temp/install.py"
"$studio_python" -X utf8 "$studio_temp/install.py" "$@"
