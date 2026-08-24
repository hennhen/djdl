from djdl.rekordbox import escape_attr, unescape_attr
from djdl.rekordbox.tags import path_to_location
from djdl.rekordbox.xml import render


def track(**over):
    base = {"title": "T", "artist": "A", "album": "", "genre": "", "kind": "M4A File",
            "total_time": 180, "bitrate": 256, "sample_rate": 44100, "size": 100,
            "location": "file://localhost/x.m4a"}
    base.update(over)
    return base


def test_ampersand_is_escaped_once_and_round_trips():
    assert escape_attr('A & B "c" <d>') == 'A &amp; B &quot;c&quot; &lt;d&gt;'
    assert unescape_attr(escape_attr('A & B "c" <d>')) == 'A & B "c" <d>'


def test_unescape_resolves_amp_last_so_encoded_entities_survive():
    # "&amp;quot;" is a literal &quot; in the text, not a quote character.
    assert unescape_attr("&amp;quot;") == "&quot;"


def test_location_percent_encodes_spaces():
    assert path_to_location("/Music/DJ Downloads/a.m4a") == \
        "file://localhost/Music/DJ%20Downloads/a.m4a"


def test_unknown_bitrate_is_omitted_rather_than_written_as_zero():
    out = render([track(bitrate=0, sample_rate=0)], "P")
    assert "BitRate" not in out and "SampleRate" not in out
    assert 'BitRate="256"' in render([track()], "P")


def test_playlist_references_every_track_in_order():
    out = render([track(title="one"), track(title="two")], "DJ Downloads")
    assert 'Entries="2"' in out
    assert '<TRACK Key="1"/>' in out and '<TRACK Key="2"/>' in out
    assert out.index('Name="one"') < out.index('Name="two"')


def test_track_titles_with_ampersands_do_not_break_the_document():
    import xml.etree.ElementTree as ET
    doc = ET.fromstring(render([track(title="Rock & Roll", artist='The "A"')], "P & Q"))
    assert doc.find(".//TRACK").get("Name") == "Rock & Roll"


def test_empty_folder_still_renders_a_valid_document():
    import xml.etree.ElementTree as ET
    doc = ET.fromstring(render([], "DJ Downloads"))
    assert doc.find("COLLECTION").get("Entries") == "0"


def test_tracks_are_newest_first_with_ties_broken_by_name(tmp_path):
    import os

    from djdl.rekordbox.tags import read_folder

    for name, mtime in (("b.m4a", 100), ("a.m4a", 100), ("c.m4a", 200)):
        f = tmp_path / name
        f.write_bytes(b"")
        os.utime(f, (mtime, mtime))
    (tmp_path / "notes.txt").write_text("ignored")

    # c is newest; a and b tie on mtime and fall back to name, every run.
    assert [t["title"] for t in read_folder(tmp_path)] == ["c", "a", "b"]
