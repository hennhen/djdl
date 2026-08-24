import json

import pytest

from djdl import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "cfg")
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    return tmp_path


def test_no_config_reads_as_none():
    assert config.load_config() is None


def test_missing_keys_are_backfilled_from_defaults():
    config.CONFIG_DIR.mkdir(parents=True)
    config.CONFIG_PATH.write_text(json.dumps({"music_dir": "/m"}))
    cfg = config.load_config()
    assert cfg["music_dir"] == "/m"
    assert cfg["format"] == "m4a"
    # xml_path is derived from the folder that was actually saved, not the default.
    assert cfg["xml_path"] == "/m/rekordbox.xml"


def test_saved_values_win_over_defaults():
    config.CONFIG_DIR.mkdir(parents=True)
    config.CONFIG_PATH.write_text(json.dumps({"music_dir": "/m", "format": "mp3-320"}))
    assert config.load_config()["format"] == "mp3-320"


def test_setting_the_folder_moves_the_xml_with_it():
    cfg = config.set_music_dir(config.default_config(), "/new/place")
    assert cfg["xml_path"] == "/new/place/rekordbox.xml"


def test_folder_paths_are_expanded():
    assert not config.set_music_dir({}, "~/Music/X")["music_dir"].startswith("~")


def test_a_corrupt_config_exits_rather_than_silently_resetting():
    config.CONFIG_DIR.mkdir(parents=True)
    config.CONFIG_PATH.write_text("{not json")
    with pytest.raises(SystemExit):
        config.load_config()
