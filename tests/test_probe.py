from djdl.doctor.steps import parse_probe, probe_verdict

# What a real run's output looks like: an info line on stderr, then the --print line.
WITH_COOKIES = "Extracted 102 cookies from safari\n140|129.506|mp4a.40.2\n"
NO_COOKIES = "141|256.0|mp4a.40.2\n"


def test_parses_cookie_count_and_format_line():
    assert parse_probe(WITH_COOKIES) == ("140", 129.506, "mp4a.40.2", 102)


def test_missing_cookie_line_reads_as_zero_cookies():
    assert parse_probe(NO_COOKIES)[3] == 0


def test_unparseable_bitrate_does_not_blow_up():
    assert parse_probe("140|NA|mp4a\n")[1] == 0.0


def test_empty_output_yields_no_format():
    assert parse_probe("")[0] == ""


def test_no_cookies_configured_is_a_clean_free_tier_pass():
    state, label, _, advice = probe_verdict("", "140", 129.0, 0)
    assert state == "ok"
    assert "free-tier" in label
    assert "Premium" in advice


def test_format_141_confirms_premium():
    state, label, _, advice = probe_verdict("safari", "141", 256.0, 102)
    assert state == "ok" and "Premium" in label and advice == ""


def test_high_bitrate_confirms_premium_even_if_the_itag_changes():
    # YouTube has renumbered its Premium audio itags before; bitrate is the backstop.
    assert probe_verdict("safari", "774", 256.0, 102)[0] == "ok"


def test_cookies_configured_but_none_loaded_blames_full_disk_access():
    state, label, _, advice = probe_verdict("safari", "140", 129.0, 0)
    assert state == "warn"
    assert "none were loaded" in label
    assert "Full Disk Access" in advice


def test_cookies_loaded_but_free_stream_does_not_blame_full_disk_access():
    # The regression this whole check exists for: a valid session getting 128k
    # is a subscription or upstream-gating question, not a local setup problem.
    state, label, _, advice = probe_verdict("safari", "140", 129.0, 102)
    assert state == "warn"
    assert "102 cookies" in label
    assert "not Full Disk Access" in advice
    assert "subscription" in advice
