"""Reading what rekordbox wants to know about an audio file."""

import re
import sys
import urllib.parse
from pathlib import Path

import mutagen

AUDIO_EXTS = (".m4a", ".mp3")


def path_to_location(path):
    """rekordbox Location URI: file://localhost/<percent-encoded absolute path>."""
    return "file://localhost" + urllib.parse.quote(str(path))


def _from_filename(name):
    """`Artist - Title` split, used until real tags say otherwise."""
    m = re.match(r"(.+?) - (.+)", name)
    return (m.group(1), m.group(2)) if m else ("", name)


def read_track(path):
    """A dict of tag data for one track, falling back to the filename."""
    artist, title = _from_filename(path.stem)
    album = genre = ""
    total_time = bitrate = sample_rate = 0

    try:
        audio = mutagen.File(str(path), easy=True)
        if audio is not None:
            if audio.tags:
                title = (audio.tags.get("title") or [title])[0]
                artist = (audio.tags.get("artist") or [artist])[0]
                album = (audio.tags.get("album") or [album])[0]
                genre = (audio.tags.get("genre") or [genre])[0]
            info = getattr(audio, "info", None)
            if info is not None:
                total_time = int(round(getattr(info, "length", 0) or 0))
                bitrate = int(getattr(info, "bitrate", 0) or 0)
                sample_rate = int(getattr(info, "sample_rate", 0) or 0)
    except Exception as e:
        print(f"djdl: could not read tags for {path.name}: {e}", file=sys.stderr)

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "genre": genre,
        "kind": "MP3 File" if path.suffix.lower() == ".mp3" else "M4A File",
        "total_time": total_time,
        "bitrate": bitrate // 1000 if bitrate else 0,  # rekordbox wants kbps
        "sample_rate": sample_rate,
        "size": path.stat().st_size,
        "location": path_to_location(path.resolve()),
    }


def read_folder(music_dir):
    """Every track in the folder, newest download first — so a track you just
    grabbed sits at the top of the playlist, right where you expect it.

    A batch of downloads routinely lands on the same second, so mtime alone
    leaves ties to be broken by directory order, which is not stable between
    runs. Name breaks the tie and keeps the playlist deterministic."""
    audio = [p for p in Path(music_dir).iterdir()
             if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    audio.sort(key=lambda p: (-p.stat().st_mtime, p.name.lower()))
    return [read_track(p) for p in audio]
