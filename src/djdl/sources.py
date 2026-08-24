"""Working out what a pasted URL actually is."""

import re
import urllib.parse

# SoundCloud pages that are a collection of tracks rather than one track.
SOUNDCLOUD_SET_SUFFIXES = ("/likes", "/tracks", "/albums", "/reposts",
                           "/popular-tracks", "/sets")


def split_urls(text):
    """Split a pasted blob into individual URLs, whether they arrived one per
    line or several jammed onto one line separated by spaces/commas."""
    return [tok for tok in re.split(r"[\s,]+", text.strip()) if tok]


def is_soundcloud(url):
    return "soundcloud.com" in url


def is_spotify(url):
    return "open.spotify.com" in url or url.startswith("spotify:")


def is_playlist(url):
    """A dedicated playlist page should be expanded; a plain track URL that
    merely carries a playlist reference should not drag in the whole playlist."""
    if is_soundcloud(url):
        # Only the path decides: a track inside a set carries the set in its
        # query string (?in=user/sets/name) and must stay a single track.
        path = urllib.parse.urlparse(url).path.rstrip("/")
        return "/sets/" in path or path.endswith(SOUNDCLOUD_SET_SUFFIXES)
    return "playlist?" in url or "/playlist" in url


def describe(url):
    """Which downloader handles this URL, for the line printed before it runs."""
    if is_spotify(url):
        return "spotdl"
    return "yt-dlp · soundcloud" if is_soundcloud(url) else "yt-dlp"
