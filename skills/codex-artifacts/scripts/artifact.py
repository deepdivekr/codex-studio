#!/usr/bin/env python3
"""Compatibility entry point for existing Codex Artifacts launch commands."""
from pathlib import Path
import runpy
import sys

script = Path(__file__).resolve().parents[2] / 'codex-studio/scripts/artifact.py'
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name='__main__')
