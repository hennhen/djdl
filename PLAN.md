# `djdl` — YouTube → M4A → rekordbox 7 download tool

## Context

Henry wants a terminal tool to download songs from YouTube in the best available quality, drop them into a configurable music folder, and get them into his rekordbox 7 library with as little clicking as possible. Requirements confirmed:

- **Input:** paste URL(s) into the terminal (as args, or an interactive prompt loop when run with no args)
- **Format:** best-quality native **M4A/AAC** (no re-encode; YouTube caps at ~128–160 kbps so transcoding to "320 MP3" adds nothing). A config option will still allow switching to `mp3-320` later if CDJ compatibility ever demands it.
- **Folder:** configurable via the tool itself — set once on first run, remembered in a config file
- **rekordbox:** version 7. Rekordbox has no true watched-folder auto-import and its database is encrypted (unsafe to write directly). The supported bridge is a **rekordbox.xml** file: the tool regenerates it after every download, and after a one-time rekordbox preference setup, new tracks appear under the "rekordbox xml" tree node — refresh and drag to Collection (2 clicks, no file browsing).

Environment (verified): yt-dlp 2025.03.27 at `~/.local/bin/yt-dlp` (old — will update), ffmpeg 8.1, Python 3.11 (anaconda), rekordbox 7 installed.

## What gets built

A single Python CLI script installed as `~/.local/bin/djdl` (no project repo; self-contained file, stdlib + `mutagen` for tag reading).

### Commands

| Command | Behavior |
|---|---|
| `djdl <url> [url ...]` | Download each URL, tag it, refresh rekordbox.xml |
| `djdl` (no args) | Interactive loop: paste a URL, it downloads; empty line or Ctrl-D quits |
| `djdl config` | Show current config |
| `djdl config folder <path>` / `djdl config format m4a\|mp3-320` | Update settings |

First run with no config triggers a short setup prompt (folder path, defaulting to `~/Music/DJ Downloads`) and saves it.

### Config file

`~/.config/djdl/config.json`:
```json
{
  "music_dir": "/Users/henrywu/Music/DJ Downloads",
  "format": "m4a",
  "playlist_name": "DJ Downloads",
  "xml_path": "<music_dir>/rekordbox.xml"
}
```

### Download step (yt-dlp via subprocess)

- Format selection: `bestaudio[ext=m4a]/bestaudio` — grabs YouTube's native AAC stream untouched; only falls back to converting (Opus→AAC) when no m4a stream exists, via `--audio-format m4a` postprocessor. (`mp3-320` config value switches to `-x --audio-format mp3 --audio-quality 320K`.)
- Tagging: `--embed-metadata --embed-thumbnail` (cover art from video thumbnail) plus `--parse-metadata` to split "Artist - Title" video names into proper artist/title tags.
- Output template: `Artist - Title.m4a` in `music_dir`, sanitized.
- Dedupe: `--download-archive <music_dir>/.archive.txt` — re-pasting a link is a no-op.
- Playlists URLs work automatically (yt-dlp expands them), single videos in playlists use `--no-playlist`.

### rekordbox.xml generation

After each run, scan `music_dir` for audio files, read tags with `mutagen`, and write a `DJ_PLAYLISTS` v1.0 XML (`rekordbox.xml`) containing a COLLECTION of all tracks + one playlist named "DJ Downloads". This is the format rekordbox officially imports.

### One-time rekordbox setup (manual, documented in tool's `djdl setup-help` output)

1. rekordbox 7 → Preferences → Advanced → Database → **rekordbox xml** → point to the generated `rekordbox.xml`
2. Preferences → View → Layout → check **rekordbox xml** so it shows in the sidebar
3. After downloading: click refresh on the rekordbox xml node, open "DJ Downloads", select-all → right-click → Import to Collection (or drag)

## Implementation steps

1. Update yt-dlp (`yt-dlp -U` or pip) — March 2025 build will likely fail against current YouTube
2. `pip install mutagen` if missing
3. Write `~/.local/bin/djdl` (Python, `#!/usr/bin/env python3`, chmod +x): config handling, yt-dlp subprocess wrapper, XML generator, interactive loop
4. First-run config setup with Henry's chosen folder

## Verification

1. `djdl config` — confirm config created correctly
2. `djdl <test URL>` using a Creative Commons/NCS track — confirm: file lands in music folder as `Artist - Title.m4a`, `ffprobe` shows AAC (no re-encode), embedded artist/title/artwork tags
3. Re-run same URL — confirm skip (dedupe works)
4. Open generated `rekordbox.xml` — valid XML, track present with correct Location URI
5. Henry does the one-time rekordbox preference setup, refreshes the xml node, confirms the track appears and imports/plays
