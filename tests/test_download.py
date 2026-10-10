import pytest

from djdl.download import build_spotdl_cmd, build_ytdlp_cmd

YT = "https://www.youtube.com/watch?v=abc"
SC = "https://soundcloud.com/user/track"


@pytest.fixture
def cfg(tmp_path):
    return {"music_dir": str(tmp_path), "format": "m4a", "cookies_browser": ""}


def flag_value(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def test_single_track_does_not_expand_a_playlist(cfg):
    assert "--no-playlist" in build_ytdlp_cmd(cfg, YT)
    assert "--yes-playlist" in build_ytdlp_cmd(
        cfg, "https://www.youtube.com/playlist?list=PL1")


def test_m4a_takes_the_native_aac_stream_untouched(cfg):
    assert flag_value(build_ytdlp_cmd(cfg, YT), "-f") == "bestaudio[ext=m4a]/bestaudio"
    assert flag_value(build_ytdlp_cmd(cfg, YT), "--audio-format") == "m4a"


def test_soundcloud_keeps_whichever_container_arrives(cfg):
    cmd = build_ytdlp_cmd(cfg, SC)
    assert flag_value(cmd, "-f").startswith("bestaudio[ext=m4a]/bestaudio[ext=mp3]")
    assert flag_value(cmd, "--audio-format") == "best"


def test_soundcloud_also_splits_the_track_tag(cfg):
    # SoundCloud's `track` field wins over the filename split when embedding.
    assert any("track:" in a for a in build_ytdlp_cmd(cfg, SC))
    assert not any("track:" in a for a in build_ytdlp_cmd(cfg, YT))


def test_mp3_320_reencodes(cfg):
    cfg["format"] = "mp3-320"
    cmd = build_ytdlp_cmd(cfg, YT)
    assert flag_value(cmd, "--audio-format") == "mp3"
    assert flag_value(cmd, "--audio-quality") == "320K"


def test_cookies_are_passed_through_to_both_tools(cfg):
    cfg["cookies_browser"] = "safari"
    assert flag_value(build_ytdlp_cmd(cfg, YT), "--cookies-from-browser") == "safari"
    spot = build_spotdl_cmd(cfg, "spotify:track:x")
    assert flag_value(spot, "--yt-dlp-args") == "--cookies-from-browser safari"


def test_spotdl_m4a_disables_the_bitrate_reencode(cfg):
    cmd = build_spotdl_cmd(cfg, "spotify:track:x")
    assert flag_value(cmd, "--format") == "m4a"
    assert flag_value(cmd, "--bitrate") == "disable"


LIKED = "https://open.spotify.com/collection/tracks"


def test_liked_songs_become_the_saved_query_with_a_login(cfg):
    cfg.update(spotify_client_id="id", spotify_client_secret="secret")
    cmd = build_spotdl_cmd(cfg, LIKED)
    assert cmd[1:3] == ["download", "saved"]
    assert LIKED not in cmd
    assert "--user-auth" in cmd
    assert flag_value(cmd, "--client-id") == "id"
    assert flag_value(cmd, "--client-secret") == "secret"


def test_ordinary_spotify_links_stay_logged_out(cfg):
    cfg.update(spotify_client_id="id", spotify_client_secret="secret")
    cmd = build_spotdl_cmd(cfg, "https://open.spotify.com/playlist/x")
    assert "--user-auth" not in cmd
    assert "--client-id" not in cmd


def test_liked_songs_without_a_login_explain_instead_of_running(cfg, monkeypatch, capsys):
    from djdl import download as dl

    def boom(*a, **k):
        raise AssertionError("spotdl should not run")

    monkeypatch.setattr(dl.subprocess, "run", boom)
    monkeypatch.setattr(dl.tools, "require", lambda name, hint: name)
    assert dl.download(cfg, LIKED) is False
    assert "djdl config spotify" in capsys.readouterr().err
