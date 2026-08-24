from djdl import sources

YT = "https://www.youtube.com/watch?v=abc123"


def test_split_urls_handles_newlines_spaces_and_commas():
    assert sources.split_urls(f"{YT}\n{YT} {YT},{YT}") == [YT] * 4
    assert sources.split_urls("   ") == []


def test_youtube_playlist_page_expands():
    assert sources.is_playlist("https://www.youtube.com/playlist?list=PL123")


def test_youtube_track_carrying_a_list_stays_one_track():
    assert not sources.is_playlist(f"{YT}&list=PL123&index=4")


def test_soundcloud_sets_and_collections_expand():
    for url in (
        "https://soundcloud.com/user/sets/my-set",
        "https://soundcloud.com/user/likes",
        "https://soundcloud.com/user/tracks/",
    ):
        assert sources.is_playlist(url), url


def test_soundcloud_track_linking_a_set_stays_one_track():
    # The set lives in the query string, not the path — only the path decides.
    url = "https://soundcloud.com/user/a-track?in=user/sets/my-set"
    assert not sources.is_playlist(url)


def test_spotify_detection_covers_urls_and_uris():
    assert sources.is_spotify("https://open.spotify.com/track/xyz")
    assert sources.is_spotify("spotify:track:xyz")
    assert not sources.is_spotify(YT)


def test_describe_names_the_downloader():
    assert sources.describe(YT) == "yt-dlp"
    assert sources.describe("spotify:track:x") == "spotdl"
    assert "soundcloud" in sources.describe("https://soundcloud.com/u/t")
