"""Reading and patching rekordbox's own preferences file.

Pointing rekordbox at a library XML is a preference (`bridgeImportedLibraryFile`)
plus a sidebar toggle (`showRbXml`). Both live in rekordbox3.settings, which
rekordbox rewrites when it quits — so it has to be closed before we touch it.
"""

import re
import subprocess
import time
from pathlib import Path

from djdl.rekordbox import escape_attr, unescape_attr
from djdl.tools import run_quiet

SETTINGS_GLOB = "Library/Application Support/Pioneer/rekordbox*/rekordbox3.settings"

SETUP_HELP = """\
One-time rekordbox 7 setup (do this once):

  1. rekordbox 7 → Preferences → Advanced → Database → "rekordbox xml"
     → set the imported library file to:
         {xml_path}

  2. Preferences → View → Layout → check "rekordbox xml"
     so it appears in the left sidebar tree.

After every `djdl` download:

  3. Click the refresh icon on the "rekordbox xml" node in the sidebar.
  4. Open the "{playlist_name}" playlist under it, select all tracks,
     right-click → "Import to Collection" (or drag them into Collection).
"""


def settings_files():
    """Every rekordbox settings file on this machine, most recent first."""
    return sorted(Path.home().glob(SETTINGS_GLOB),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def read_setting(text, key):
    m = re.search(rf'<VALUE\s+name="{re.escape(key)}"\s+val="([^"]*)"\s*/>', text)
    # Values are XML-escaped in the file; compare against real paths, not entities.
    return unescape_attr(m.group(1)) if m else None


def apply_settings(text, updates):
    """The settings file text with `updates` written into it."""
    for key, value in updates.items():
        escaped = escape_attr(value)
        pattern = rf'(<VALUE\s+name="{re.escape(key)}"\s+val=")[^"]*("\s*/>)'
        if re.search(pattern, text):
            text = re.sub(pattern, lambda m: m.group(1) + escaped + m.group(2), text)
        else:
            text = text.replace(
                "</PROPERTIES>",
                f'  <VALUE name="{key}" val="{escaped}"/>\n</PROPERTIES>',
            )
    return text


def write_settings(path, updates):
    """Patch the settings file in place, backing it up first."""
    text = path.read_text(encoding="utf-8")
    backup = path.with_suffix(path.suffix + ".djdl-backup")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    path.write_text(apply_settings(text, updates), encoding="utf-8")
    return backup


def is_running():
    return run_quiet(["pgrep", "-x", "rekordbox"])[0] == 0


def quit_app(timeout=30):
    subprocess.run(["osascript", "-e", 'quit app "rekordbox"'],
                   capture_output=True, text=True)
    for _ in range(timeout):
        if not is_running():
            return True
        time.sleep(1)
    return False
