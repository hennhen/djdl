from djdl.rekordbox.settings import apply_settings, read_setting

DOC = """<?xml version="1.0"?>
<PROPERTIES>
  <VALUE name="showRbXml" val="0"/>
  <VALUE name="other" val="keep me"/>
</PROPERTIES>
"""


def test_reads_an_existing_value():
    assert read_setting(DOC, "showRbXml") == "0"
    assert read_setting(DOC, "notThere") is None


def test_reads_paths_unescaped_so_they_compare_against_real_paths():
    doc = '<VALUE name="f" val="/a &amp; b/rekordbox.xml"/>'
    assert read_setting(doc, "f") == "/a & b/rekordbox.xml"


def test_existing_key_is_replaced_not_duplicated():
    out = apply_settings(DOC, {"showRbXml": "1"})
    assert out.count('name="showRbXml"') == 1
    assert read_setting(out, "showRbXml") == "1"
    assert read_setting(out, "other") == "keep me"


def test_missing_key_is_appended_inside_properties():
    out = apply_settings(DOC, {"bridgeImportedLibraryFile": "/m/rekordbox.xml"})
    assert read_setting(out, "bridgeImportedLibraryFile") == "/m/rekordbox.xml"
    assert out.index("bridgeImportedLibraryFile") < out.index("</PROPERTIES>")


def test_a_path_with_an_ampersand_is_escaped_on_write_and_read_back_whole():
    path = "/Volumes/DJ & Co/rekordbox.xml"
    out = apply_settings(DOC, {"bridgeImportedLibraryFile": path})
    assert "&amp;" in out
    assert read_setting(out, "bridgeImportedLibraryFile") == path
