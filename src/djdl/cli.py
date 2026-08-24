"""Command dispatch: turning argv into one of djdl's commands."""

USAGE = """\
djdl — download tracks and bridge them into rekordbox 7.

Usage:
  djdl <url> [url ...]              Download each URL, tag it, refresh rekordbox.xml
  djdl                              Interactive loop: paste links until you're done
  djdl setup                        Guided setup: tools, config, cookies, rekordbox link
  djdl doctor                       The same checks, read-only — exits 1 if broken
  djdl config                       Show current config
  djdl config folder <path>         Set the music folder
  djdl config format m4a|mp3-320    Set the download format
  djdl config cookies <browser>     Read login cookies from a browser (Premium quality)
  djdl setup-help                   Print the rekordbox preference steps to do by hand
"""

import json
import select
import sys

from djdl.config import (VALID_BROWSERS, VALID_FORMATS, default_config,
                         ensure_config, load_config, playlist_name,
                         save_config, set_music_dir)
from djdl.download import download
from djdl.rekordbox import xml as rbxml
from djdl.rekordbox.settings import SETUP_HELP
from djdl.sources import split_urls


def cmd_config(args):
    cfg = load_config()
    if not args:
        if cfg is None:
            print("No config yet. Run `djdl setup` to set one up.")
            return 0
        print(json.dumps(cfg, indent=2))
        return 0

    if cfg is None:
        cfg = default_config()

    key, value = args[0], args[1] if len(args) > 1 else None
    if key == "folder":
        if value is None:
            sys.exit("usage: djdl config folder <path>")
        set_music_dir(cfg, value)
        save_config(cfg)
        print(f"music_dir = {cfg['music_dir']}")
        print(f"xml_path  = {cfg['xml_path']}")
    elif key == "format":
        if value not in VALID_FORMATS:
            sys.exit(f"usage: djdl config format {'|'.join(VALID_FORMATS)}")
        cfg["format"] = value
        save_config(cfg)
        print(f"format = {cfg['format']}")
    elif key == "cookies":
        choice = (value or "").lower()
        if choice in ("off", "none"):
            cfg["cookies_browser"] = ""
        elif choice in VALID_BROWSERS:
            cfg["cookies_browser"] = choice
        else:
            sys.exit(f"usage: djdl config cookies {'|'.join(VALID_BROWSERS)}|off")
        save_config(cfg)
        print(f"cookies_browser = {cfg['cookies_browser'] or '(off)'}")
    else:
        sys.exit(f"djdl: unknown config key '{key}'")
    return 0


def cmd_setup_help():
    cfg = load_config() or default_config()
    print(SETUP_HELP.format(xml_path=cfg["xml_path"], playlist_name=playlist_name(cfg)))
    return 0


def run_downloads(cfg, urls):
    """Download every URL, then refresh the xml. Returns True if any succeeded."""
    results = [download(cfg, url) for url in urls]
    # Always regenerate: the xml should reflect the folder, not just this batch.
    rbxml.generate(cfg)
    return any(results)


def drain_pasted_lines():
    """After input() returns one line, grab any further lines pasted alongside it
    and already sitting in the buffer, so a multi-link paste is one batch."""
    lines = []
    while select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if not line:
            break
        lines.append(line.rstrip("\n"))
    return lines


def interactive_loop(cfg):
    print("djdl interactive — paste one or more links and press Enter.")
    print("Blank line or Ctrl-D to quit.\n")
    while True:
        try:
            line = input("url> ").strip()
        except EOFError:
            print()
            break
        if not line:
            break
        pasted = [line] + drain_pasted_lines()
        run_downloads(cfg, [u for l in pasted for u in split_urls(l)])
    print("bye.")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else None

    if command in ("-h", "--help", "help"):
        print(USAGE.rstrip())
        return 0
    if command == "config":
        return cmd_config(argv[1:])
    if command == "setup-help":
        return cmd_setup_help()
    if command in ("setup", "doctor", "check"):
        from djdl.doctor.steps import run
        return run(fix=command == "setup")

    cfg = ensure_config()
    if not argv:
        return interactive_loop(cfg)
    urls = [u for a in argv for u in split_urls(a)]
    # Exit non-zero when nothing came down, so scripts and `&&` chains can tell.
    return 0 if run_downloads(cfg, urls) else 1


if __name__ == "__main__":
    sys.exit(main())
