# djdl

Paste a YouTube, SoundCloud or Spotify link into your terminal, get a properly tagged
**M4A/AAC** file in your music folder, and have it show up in **rekordbox 7** — no file
browsing, no re-encoding.

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

- **YouTube + SoundCloud + Spotify** — YouTube and SoundCloud URLs go through `yt-dlp`;
  `open.spotify.com` links go through `spotdl` (which matches tracks to YouTube Music under the
  hood). Same folder, same tagging, same XML.
- **SoundCloud, at the best quality it offers** — SoundCloud serves 160k AAC on many tracks and
  128k MP3 on all of them; djdl takes the better of the two and keeps the container it arrives
  in rather than re-encoding one lossy format into another. Sets (`/sets/`, `/likes`, `/tracks`,
  `/albums`) expand into all their tracks; a single track that merely *links* a set
  (`?in=user/sets/…`) stays a single track.
- **No lossy re-encode** — grabs the native AAC stream (`bestaudio[ext=m4a]`) untouched. A `mp3-320`
  format option exists if a CDJ ever demands it.
- **256k with YouTube Premium** — point it at a browser you're logged into and it pulls format 141
  (~256 kbps AAC) instead of the default 128k. See [Premium quality](#premium-quality-256k-aac).
- **Real tags + artwork** — embeds metadata and the video thumbnail as cover art, and splits
  `"Artist - Title"` video names into proper artist/title tags.
- **Dedupe** — a download archive means re-pasting a link you already have is a no-op.
- **Playlists** — YouTube playlist URLs and SoundCloud sets expand; a track URL that merely
  carries `&list=` or `?in=` does not.
- **Interactive mode** — run with no args and paste links one after another until you're done.

## Requirements

Installed for you as dependencies — you don't chase these:

| | |
|---|---|
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) + `yt-dlp-ejs` | the downloader, and the helper for YouTube's JS challenge |
| [`mutagen`](https://mutagen.readthedocs.io/) | tag + bitrate reading for the XML |
| [`spotdl`](https://github.com/spotDL/spotify-downloader) | only with the `spotify` extra |

Must already be on the system — these aren't Python packages:

| | |
|---|---|
| Python 3.11+ | |
| `ffmpeg` + `ffprobe` | yt-dlp muxes and embeds artwork with them — not optional |
| [`deno`](https://deno.com/) | only for the YouTube Premium (256k) path |
| rekordbox 7 | for the XML import side |

## Install

With [uv](https://docs.astral.sh/uv/) (recommended — djdl gets its own isolated
environment and lands on your `PATH` as `djdl`):

```bash
brew install ffmpeg deno                       # the non-Python half
uv tool install 'djdl[spotify] @ git+https://github.com/hennhen/djdl'
djdl setup
```

Drop `[spotify]` if you only use YouTube and SoundCloud — it pulls in a large
dependency tree for Spotify link matching. `pipx install` works the same way.

To upgrade — this also pulls a fresh `yt-dlp`, which is what usually needs it:

```bash
uv tool upgrade djdl
```

`djdl setup` is a guided, re-runnable wizard that does the whole job from the terminal — no
hunting through folders, no editing JSON, no clicking around rekordbox's preferences:

1. **Tools** — checks `ffmpeg`/`ffprobe` and `deno` and offers to `brew install` anything
   missing. Also flags a stale `yt-dlp`, which is the usual reason downloads suddenly break,
   and offers to upgrade it.
2. **Music folder** — asks where tracks should go and writes `~/.config/djdl/config.json`.
3. **Quality** — asks whether you have YouTube Premium, sets the cookie browser, and checks
   macOS Full Disk Access (offering to open the right settings pane if it's missing).
4. **rekordbox.xml** — creates the file, because rekordbox can't be pointed at one that
   doesn't exist yet.
5. **The rekordbox link** — reads rekordbox's own settings, and if the XML isn't wired up it
   offers to write both preferences for you (backing the file up first). rekordbox must be
   closed, and setup can quit it for you.
6. **Live check** — asks YouTube what quality it would serve, without downloading anything.

Every step is a yes/no prompt, and re-running is safe: anything already correct shows a ✓ and
is left alone. Run `djdl doctor` any time for the same report without changing a thing — it
exits non-zero if something's broken, so it works in a script.

## Usage

| Command | What it does |
|---|---|
| `djdl <url> [url ...]` | Download each URL (YouTube, SoundCloud, Spotify), tag it, regenerate `rekordbox.xml` |
| `djdl` | Interactive loop — paste a URL to download; blank line or Ctrl-D quits |
| `djdl setup` | Guided setup — tools, config, cookies, the rekordbox link. Re-run any time |
| `djdl doctor` | The same checks, read-only. Changes nothing, exits 1 if something's wrong |
| `djdl config` | Print the current config |
| `djdl config folder <path>` | Set the music folder (also moves `rekordbox.xml`) |
| `djdl config format m4a\|mp3-320` | Set the download format |
| `djdl config cookies safari\|chrome\|firefox\|brave\|edge\|off` | Set which browser to read login cookies from |
| `djdl setup-help` | Print the rekordbox preference steps to do by hand |

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

`djdl setup` does this for you — it writes both preferences into rekordbox's own settings file
(with a backup) while rekordbox is closed. To do it by hand instead:

1. **Preferences → Advanced → Database → rekordbox xml** → set the imported library file to your
   `xml_path`.
2. **Preferences → View → Layout** → check **rekordbox xml** so it appears in the sidebar.

Then after each download: click refresh on the **rekordbox xml** node, open the playlist under it,
select all → right-click → **Import to Collection**.

## Premium quality (256k AAC)

Without cookies YouTube serves ~128 kbps. With a YouTube Premium login it serves ~256 kbps AAC
(format 141). `djdl setup` walks you through this, or by hand:

```bash
djdl config cookies safari   # or whichever browser you're logged into
brew install deno            # yt-dlp needs it to solve YouTube's JS challenge
```

On macOS, the terminal running `djdl` also needs **Full Disk Access**
(System Settings → Privacy & Security → Full Disk Access) to read the browser's cookie store.
Grant it to the terminal app itself, then quit and reopen it.

Troubleshooting:

- `Operation not permitted … binarycookies` → Full Disk Access is missing.
- `Only images are available for download` → Deno is missing or stale (`brew upgrade deno`).
- `Requested format is not available` on every video → `yt-dlp` is stale; `djdl setup` offers
  to upgrade it.
- Everything looks right but you still get 128k → YouTube periodically breaks the player client
  yt-dlp relies on for the Premium streams. That's upstream, not your setup; upgrading `yt-dlp`
  after a fix lands restores it. `djdl doctor` tells you which side of this you're on.

Note that ~256k AAC is the ceiling for this pipeline — there is no lossless path from YouTube. For
that you want a store like Beatport or Bandcamp.

## Development

```bash
uv sync --all-extras   # dev environment
uv run pytest          # the test suite
uv run djdl doctor     # run it without installing
```

Layout:

```
src/djdl/
├── cli.py             argv → command, the interactive loop
├── config.py          ~/.config/djdl/config.json
├── sources.py         what a pasted URL is (track / set / playlist / Spotify)
├── download.py        building the yt-dlp and spotdl commands
├── tools.py           finding and running external executables
├── rekordbox/
│   ├── tags.py        reading tags off the files
│   ├── xml.py         rendering rekordbox.xml
│   └── settings.py    patching rekordbox's own preferences file
└── doctor/
    ├── ui.py          report lines and prompts
    └── steps.py       the setup / doctor checks
```

djdl shells out to the `yt-dlp` binary rather than importing it: the CLI flags are its stable,
documented interface where the Python API explicitly isn't, the progress bar comes for free, and
a command that fails can be copy-pasted and run by hand.
