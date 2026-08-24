"""Locating and running the external programs djdl leans on.

yt-dlp and spotdl are declared dependencies, so they are installed into the
same environment as djdl itself — look next to the running interpreter before
falling back to PATH, because a `uv tool` venv's bin directory is not on PATH.
ffmpeg and deno are not Python packages and have to come from the system.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_MACOS = sys.platform == "darwin"


def bundled(name):
    """An executable installed alongside djdl's own interpreter, if present."""
    candidate = Path(sys.executable).parent / name
    if candidate.exists() and os.access(str(candidate), os.X_OK):
        return str(candidate)
    return None


def find_exe(name):
    """Our own environment first, then PATH."""
    return bundled(name) or shutil.which(name)


def require(name, hint):
    exe = find_exe(name)
    if exe is None:
        sys.exit(f"djdl: {name} not found. {hint}")
    return exe


def find_brew():
    brew = shutil.which("brew")
    if brew:
        return brew
    for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.exists(candidate):
            return candidate
    return None


def run(cmd):
    """Run a command with its output going straight to the terminal."""
    try:
        return subprocess.run(cmd).returncode
    except (FileNotFoundError, KeyboardInterrupt):
        return 1


def run_quiet(cmd, timeout=None):
    """Run a command and capture everything it said. Returns (rc, output)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
