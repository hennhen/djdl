"""Generating the rekordbox.xml library file."""

from pathlib import Path

from djdl.config import playlist_name
from djdl.rekordbox import escape_attr
from djdl.rekordbox.tags import read_folder


def _track_element(track_id, t):
    attrs = [
        f'TrackID="{track_id}"',
        f'Name="{escape_attr(t["title"])}"',
        f'Artist="{escape_attr(t["artist"])}"',
        f'Album="{escape_attr(t["album"])}"',
        f'Genre="{escape_attr(t["genre"])}"',
        f'Kind="{escape_attr(t["kind"])}"',
        f'Size="{t["size"]}"',
        f'TotalTime="{t["total_time"]}"',
    ]
    # rekordbox reads an explicit zero as "0 kbps" rather than "unknown", so
    # leave these out entirely when mutagen couldn't determine them.
    if t["bitrate"]:
        attrs.append(f'BitRate="{t["bitrate"]}"')
    if t["sample_rate"]:
        attrs.append(f'SampleRate="{t["sample_rate"]}"')
    attrs.append(f'Location="{t["location"]}"')
    return f'    <TRACK {" ".join(attrs)}/>'


def render(tracks, playlist):
    """The full XML document for a list of tracks, as a string."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<DJ_PLAYLISTS Version="1.0.0">',
        '  <PRODUCT Name="djdl" Version="1.0" Company="djdl"/>',
        f'  <COLLECTION Entries="{len(tracks)}">',
    ]
    lines += [_track_element(i, t) for i, t in enumerate(tracks, start=1)]
    lines += [
        '  </COLLECTION>',
        '  <PLAYLISTS>',
        '    <NODE Type="0" Name="ROOT" Count="1">',
        f'      <NODE Name="{escape_attr(playlist)}" Type="1" '
        f'KeyType="0" Entries="{len(tracks)}">',
    ]
    lines += [f'        <TRACK Key="{i}"/>' for i in range(1, len(tracks) + 1)]
    lines += [
        '      </NODE>',
        '    </NODE>',
        '  </PLAYLISTS>',
        '</DJ_PLAYLISTS>',
    ]
    return "\n".join(lines) + "\n"


def generate(cfg):
    """Rewrite rekordbox.xml from whatever is in the music folder right now."""
    tracks = read_folder(cfg["music_dir"])
    xml_path = Path(cfg["xml_path"])
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(render(tracks, playlist_name(cfg)), encoding="utf-8")
    print(f"✓ rekordbox.xml updated ({len(tracks)} tracks) → {xml_path}")
