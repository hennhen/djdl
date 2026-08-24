"""The on-disk config: ~/.config/djdl/config.json."""

import json
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "djdl"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_MUSIC_DIR = Path.home() / "Music" / "DJ Downloads"
DEFAULT_PLAYLIST_NAME = "DJ Downloads"
VALID_FORMATS = ("m4a", "mp3-320")
VALID_BROWSERS = ("chrome", "safari", "firefox", "brave", "edge")


def default_config(music_dir=DEFAULT_MUSIC_DIR):
    music_dir = Path(music_dir).expanduser()
    return {
        "music_dir": str(music_dir),
        "format": "m4a",
        "playlist_name": DEFAULT_PLAYLIST_NAME,
        "xml_path": str(music_dir / "rekordbox.xml"),
        # Browser to read YouTube login cookies from (unlocks 256k AAC with
        # YouTube Premium). Empty string = no cookies (128k ceiling).
        "cookies_browser": "",
    }


def load_config():
    """The saved config, or None if there isn't one yet."""
    if not CONFIG_PATH.exists():
        return None
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        sys.exit(f"djdl: could not read config at {CONFIG_PATH}: {e}")
    # Backfill any missing keys against the defaults for this music folder.
    merged = default_config(cfg.get("music_dir", DEFAULT_MUSIC_DIR))
    merged.update(cfg)
    return merged


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


def set_music_dir(cfg, path):
    """Point the config at a music folder, keeping xml_path in step with it."""
    music_dir = Path(path).expanduser()
    cfg["music_dir"] = str(music_dir)
    cfg["xml_path"] = str(music_dir / "rekordbox.xml")
    return cfg


def playlist_name(cfg):
    return cfg.get("playlist_name", DEFAULT_PLAYLIST_NAME)


def first_run_setup():
    print("djdl — first-run setup")
    print(f"Where should downloaded tracks go? [{DEFAULT_MUSIC_DIR}]")
    try:
        answer = input("Folder: ").strip()
    except EOFError:
        answer = ""
    cfg = default_config(answer or DEFAULT_MUSIC_DIR)
    Path(cfg["music_dir"]).mkdir(parents=True, exist_ok=True)
    save_config(cfg)
    print(f"Saved config to {CONFIG_PATH}")
    print(f"Music folder: {cfg['music_dir']}")
    print(f"rekordbox.xml: {cfg['xml_path']}")
    print("\nRun `djdl setup` to check your tools and wire up rekordbox.\n")
    return cfg


def ensure_config():
    """The config to run with, creating one on first use."""
    cfg = load_config() or first_run_setup()
    Path(cfg["music_dir"]).mkdir(parents=True, exist_ok=True)
    return cfg
