"""Building and running the yt-dlp / spotdl commands.

We shell out rather than importing yt-dlp: its CLI flags are the stable,
documented interface (the Python API explicitly is not), the progress bar
comes for free, and a failing command can be copy-pasted and run by hand.
"""

import os
import subprocess
import sys

from djdl import sources, tools

YTDLP_HINT = "It ships with djdl — reinstall with `uv tool install --force djdl`."
SPOTDL_HINT = "Spotify links need it: `uv tool install --force 'djdl[spotify]'`."


def build_ytdlp_cmd(cfg, url, exe="yt-dlp"):
    music_dir = cfg["music_dir"]
    cmd = [
        exe,
        "--ignore-config",
        "--yes-playlist" if sources.is_playlist(url) else "--no-playlist",
        "--download-archive", os.path.join(music_dir, ".archive.txt"),
        "-o", os.path.join(music_dir, "%(artist,uploader)s - %(title)s.%(ext)s"),
        "--embed-metadata",
        "--embed-thumbnail",
        # Split "Artist - Title" video names into proper artist/title tags.
        "--parse-metadata", "title:(?P<artist>.+?) - (?P<title>.+)",
    ]

    if sources.is_soundcloud(url):
        # SoundCloud also fills `track` with the full "Artist - Title" string,
        # and that field wins when tags are embedded — so the split above would
        # show up in the filename but not in the tag. Split it the same way.
        cmd += ["--parse-metadata", "track:.+? - (?P<track>.+)"]

    if cfg["format"] == "mp3-320":
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "320K"]
    elif sources.is_soundcloud(url):
        # SoundCloud serves 160k AAC on many tracks and 128k MP3 on all of them.
        # Take the better of the two and keep the container it arrives in —
        # re-encoding one lossy format into another only throws away more.
        cmd += ["-f", "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
                "-x", "--audio-format", "best"]
    else:  # m4a: grab best AAC untouched (256k with Premium cookies, else 128k)
        cmd += ["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "m4a"]

    if cfg.get("cookies_browser"):
        cmd += ["--cookies-from-browser", cfg["cookies_browser"]]

    cmd.append(url)
    return cmd


def build_spotdl_cmd(cfg, url, exe="spotdl"):
    cmd = [
        exe, "download", url,
        "--output", os.path.join(cfg["music_dir"], "{artists} - {title}.{output-ext}"),
        "--print-errors",
    ]
    if cfg["format"] == "mp3-320":
        cmd += ["--format", "mp3", "--bitrate", "320k"]
    else:
        # Keep the matched audio stream untouched (no lossy re-encode); AAC/m4a
        # is what CDJs and rekordbox want.
        cmd += ["--format", "m4a", "--bitrate", "disable"]

    if cfg.get("cookies_browser"):
        # spotdl uses yt-dlp under the hood; pass Premium cookies through so it
        # can fetch the 256k AAC stream from YouTube Music.
        cmd += ["--yt-dlp-args", f"--cookies-from-browser {cfg['cookies_browser']}"]
    return cmd


def download(cfg, url):
    """Fetch one URL. Returns True if the downloader was happy."""
    if sources.is_spotify(url):
        cmd = build_spotdl_cmd(cfg, url, tools.require("spotdl", SPOTDL_HINT))
    else:
        cmd = build_ytdlp_cmd(cfg, url, tools.require("yt-dlp", YTDLP_HINT))

    tool = sources.describe(url)
    print(f"\n▶ downloading ({tool}): {url}")
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print(f"djdl: {tool} exited with code {rc} for {url}", file=sys.stderr)
    return rc == 0
