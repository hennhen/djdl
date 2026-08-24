# djdl

Paste a YouTube or Spotify link into your terminal, get a properly tagged **M4A/AAC** file in your
music folder, and have it show up in **rekordbox 7** — no file browsing, no re-encoding.

```
$ djdl https://www.youtube.com/watch?v=...
[djdl] yt-dlp: Deep House Mix - Artist Name
[djdl] wrote /Users/you/Music/USB/rekordbox.xml
```

## Why

Rekordbox has no watched-folder auto-import, and its database is encrypted (writing to it directly is
unsafe). The officially supported bridge is a `rekordbox.xml` library file. `djdl` regenerates that
file after every download, so new tracks appear under the **rekordbox xml** node in the sidebar —
refresh, select, import. Two clicks.

## Features

- **YouTube + Spotify** — YouTube URLs go through `yt-dlp`; `open.spotify.com` links go through
  `spotdl` (which matches tracks to YouTube Music under the hood). Same folder, same tagging, same XML.
- **No lossy re-encode** — grabs the native AAC stream (`bestaudio[ext=m4a]`) untouched. A `mp3-320`
  format option exists if a CDJ ever demands it.
- **256k with YouTube Premium** — point it at a browser you're logged into and it pulls format 141
  (~256 kbps AAC) instead of the default 128k. See [Premium quality](#premium-quality-256k-aac).
- **Real tags + artwork** — embeds metadata and the video thumbnail as cover art, and splits
  `"Artist - Title"` video names into proper artist/title tags.
- **Dedupe** — a download archive means re-pasting a link you already have is a no-op.
- **Playlists** — playlist URLs expand; a video URL that merely carries `&list=` does not.
- **Interactive mode** — run with no args and paste links one after another until you're done.

## Requirements

| | |
|---|---|
| Python 3.8+ | stdlib only, no packages needed for the core tool |
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | on `PATH` or at `~/.local/bin/yt-dlp` — keep it updated |
| `ffmpeg` | used by yt-dlp for muxing/thumbnail embedding |
| [`spotdl`](https://github.com/spotDL/spotify-downloader) | optional, only for Spotify links |
| [`mutagen`](https://mutagen.readthedocs.io/) | optional, improves tag reading for the XML |
| rekordbox 7 | for the XML import side |

## Install

```bash
git clone https://github.com/hennhen/djdl.git
install -m 755 djdl/djdl ~/.local/bin/djdl
```

Make sure `~/.local/bin` is on your `PATH`. First run prompts for a music folder and writes
`~/.config/djdl/config.json`.

## Usage

| Command | What it does |
|---|---|
| `djdl <url> [url ...]` | Download each URL, tag it, regenerate `rekordbox.xml` |
| `djdl` | Interactive loop — paste a URL to download; blank line or Ctrl-D quits |
| `djdl config` | Print the current config |
| `djdl config folder <path>` | Set the music folder (also moves `rekordbox.xml`) |
| `djdl config format m4a\|mp3-320` | Set the download format |
| `djdl config cookies safari\|chrome\|firefox\|brave\|edge\|off` | Set which browser to read login cookies from |
| `djdl setup-help` | Print the one-time rekordbox setup steps |

## Config

`~/.config/djdl/config.json`:

```json
{
  "music_dir": "/Users/you/Music/USB",
  "format": "m4a",
  "playlist_name": "USB",
  "xml_path": "/Users/you/Music/USB/rekordbox.xml",
  "cookies_browser": "safari"
}
```

## rekordbox setup (once)

1. **Preferences → Advanced → Database → rekordbox xml** → set the imported library file to your
   `xml_path`.
2. **Preferences → View → Layout** → check **rekordbox xml** so it appears in the sidebar.

Then after each download: click refresh on the **rekordbox xml** node, open the playlist under it,
select all → right-click → **Import to Collection**.

## Premium quality (256k AAC)

Without cookies YouTube serves ~128 kbps. With a YouTube Premium login it serves ~256 kbps AAC. To
get that:

```bash
djdl config cookies safari   # or whichever browser you're logged into
brew install deno            # yt-dlp needs it to solve YouTube's JS challenge
```

On macOS, the terminal running `djdl` also needs **Full Disk Access**
(System Settings → Privacy & Security → Full Disk Access) to read the browser's cookie store.

Troubleshooting:

- `Operation not permitted … binarycookies` → Full Disk Access is missing.
- `Only images are available for download` → Deno is missing or stale (`brew upgrade deno`).

Note that ~256k AAC is the ceiling for this pipeline — there is no lossless path from YouTube. For
that you want a store like Beatport or Bandcamp.

## Design notes

[PLAN.md](PLAN.md) has the original design write-up: format selection reasoning, the XML schema
choice, and why the rekordbox database isn't written directly.
