"""The individual checks `djdl setup` (fix=True) and `djdl doctor` (fix=False) run.

Every step returns a list of blockers: things that will stop djdl working and
that this run could not resolve. An empty list means that step is fine.
"""

import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from djdl import tools
from djdl.config import (CONFIG_PATH, VALID_BROWSERS, default_config,
                         load_config, playlist_name, save_config, set_music_dir)
from djdl.doctor.ui import (ask_choice, ask_text, ask_yes, heading, interactive,
                            note, paint, report, title)
from djdl.rekordbox import settings as rbsettings
from djdl.rekordbox import xml as rbxml

# yt-dlp gets stale fast — YouTube changes something every few weeks.
YTDLP_STALE_DAYS = 30
# Read-only quality probe. This has to be a track that *does* offer format 141
# (256k AAC) to a Premium session, or the probe can't tell a broken setup from a
# video that simply has no high-quality stream. Monstercat uploads do.
PROBE_URL = "https://www.youtube.com/watch?v=LDU_Txk06tM"

# Things that are not Python packages, so djdl's own install can't supply them.
SYSTEM_DEPS = (
    {"name": "ffmpeg", "required": True, "brew": "ffmpeg",
     "why": "extracts audio, embeds tags + artwork"},
    {"name": "ffprobe", "required": True, "brew": "ffmpeg",
     "why": "reads stream info (ships with ffmpeg)"},
    {"name": "deno", "required": False, "brew": "deno",
     "why": "solves YouTube's JS challenge — needed for Premium cookies"},
)

SAFARI_COOKIE_PATHS = (
    Path.home() / "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies",
    Path.home() / "Library/Cookies/Cookies.binarycookies",
)
BROWSER_DATA_DIRS = {
    "chrome": Path.home() / "Library/Application Support/Google/Chrome",
    "brave": Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser",
    "edge": Path.home() / "Library/Application Support/Microsoft Edge",
    "firefox": Path.home() / "Library/Application Support/Firefox",
}
TERM_APP_NAMES = {
    "Apple_Terminal": "Terminal",
    "iTerm.app": "iTerm",
    "WarpTerminal": "Warp",
    "vscode": "Visual Studio Code",
    "Hyper": "Hyper",
    "ghostty": "Ghostty",
    "kitty": "kitty",
    "alacritty": "Alacritty",
}


def run_visible(cmd):
    print(paint(f"    $ {' '.join(cmd)}", "90"))
    return tools.run(cmd)


def install_with_brew(package):
    brew = tools.find_brew()
    if not brew:
        report("bad", "Homebrew is not installed", "it's the easiest way to get the rest")
        note('Install it with:\n'
             '  /bin/bash -c "$(curl -fsSL '
             'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n'
             "Then run the two `eval` lines it prints, and re-run `djdl setup`.")
        return False
    return run_visible([brew, "install", package]) == 0


# ---- 1. tools ------------------------------------------------------------- #
def ytdlp_age():
    """(version, days since release) for the installed yt-dlp — its version is a date."""
    exe = tools.find_exe("yt-dlp")
    if not exe:
        return None, None
    rc, out = tools.run_quiet([exe, "--version"], timeout=30)
    version = out.strip().splitlines()[-1].strip() if out.strip() else ""
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", version)
    if rc != 0 or not m:
        return version or None, None
    released = datetime.date(*(int(g) for g in m.groups()))
    return version, (datetime.date.today() - released).days


def upgrade_djdl():
    """yt-dlp is one of our dependencies, so upgrading djdl upgrades it too."""
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if os.path.exists(uv):
        return run_visible([uv, "tool", "upgrade", "djdl"]) == 0
    return run_visible([sys.executable, "-m", "pip", "install", "--upgrade",
                        "yt-dlp", "yt-dlp-ejs"]) == 0


def step_ytdlp(fix):
    version, age = ytdlp_age()
    if version is None:
        report("bad", "yt-dlp missing", "it ships with djdl, so this install is broken")
        return ["yt-dlp is missing — reinstall with `uv tool install --force djdl`"]
    if age is None:
        report("info", f"yt-dlp {version}", "couldn't read its release date")
        return []
    if age <= YTDLP_STALE_DAYS:
        report("ok", f"yt-dlp {version}", f"{age} days old")
        return []

    report("warn", f"yt-dlp {version} is {age} days old",
           "stale yt-dlp is the usual cause of sudden failures")
    if fix and ask_yes("Upgrade it now (upgrades djdl and its deps)?", default=True):
        if upgrade_djdl():
            report("ok", f"yt-dlp now {ytdlp_age()[0]}")
        else:
            report("bad", "the upgrade failed", "try `uv tool upgrade djdl` by hand")
    return []


def step_tools(fix):
    heading("1. Tools djdl needs")
    blockers = []
    for dep in SYSTEM_DEPS:
        path = tools.find_exe(dep["name"])
        if path:
            report("ok", dep["name"], path)
            continue

        report("bad" if dep["required"] else "warn",
               f"{dep['name']} missing", dep["why"])
        installed = False
        if fix and ask_yes(f"Install {dep['name']} now?", default=dep["required"]):
            installed = install_with_brew(dep["brew"]) and bool(tools.find_exe(dep["name"]))
            report("ok" if installed else "bad",
                   f"{dep['name']} installed" if installed else f"{dep['name']} still missing")
        if not installed and dep["required"]:
            blockers.append(f"{dep['name']} is required — install it and re-run `djdl setup`")

    if tools.find_exe("spotdl"):
        report("ok", "spotdl", "Spotify links will work")
    else:
        report("info", "spotdl not installed",
               "only needed for Spotify links — `uv tool install --force 'djdl[spotify]'`")

    return blockers + step_ytdlp(fix)


# ---- 2. config ------------------------------------------------------------ #
def step_config(fix):
    heading("2. Where your music lives")
    cfg = load_config()
    first_time = cfg is None
    if first_time:
        cfg = default_config()
        report("info", "no config yet", str(CONFIG_PATH))
    else:
        report("ok", "config found", str(CONFIG_PATH))

    if fix and (first_time or ask_yes(f"Music folder is {cfg['music_dir']}. Change it?",
                                      default=False)):
        set_music_dir(cfg, ask_text("Folder for downloaded tracks", cfg["music_dir"]))

    music_dir = Path(cfg["music_dir"])
    if music_dir.parts[:2] == ("/", "Volumes") and not music_dir.exists():
        report("warn", "that folder is on a volume that isn't mounted", str(music_dir))

    if music_dir.exists():
        report("ok", "music folder", str(music_dir))
    elif not fix:
        # doctor changes nothing — just say what setup would do.
        report("warn", "music folder doesn't exist yet", str(music_dir))
        return cfg, ["music folder doesn't exist yet — run `djdl setup`"]
    else:
        try:
            music_dir.mkdir(parents=True, exist_ok=True)
            report("ok", "music folder created", str(music_dir))
        except OSError as e:
            report("bad", "cannot create the music folder", str(e))
            return cfg, [f"music folder {music_dir} is not usable: {e}"]

    if not os.access(str(music_dir), os.W_OK):
        report("bad", "music folder is not writable", str(music_dir))
        return cfg, [f"music folder {music_dir} is not writable"]

    if fix:
        save_config(cfg)
    report("ok", f"format: {cfg['format']}", "change with `djdl config format m4a|mp3-320`")
    report("ok", f"playlist name: {playlist_name(cfg)}")
    return cfg, []


# ---- 3. cookies ----------------------------------------------------------- #
def terminal_app_name():
    term = os.environ.get("TERM_PROGRAM", "")
    return TERM_APP_NAMES.get(term, term or "your terminal app")


def safari_cookie_access():
    """('ok'|'denied'|'missing', path) — 'denied' means Full Disk Access is off."""
    for path in SAFARI_COOKIE_PATHS:
        try:
            with open(path, "rb") as f:
                f.read(4)
            return "ok", path
        except PermissionError:
            return "denied", path
        except FileNotFoundError:
            continue
        except OSError:
            return "denied", path
    return "missing", None


def open_full_disk_access_pane():
    subprocess.run([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
    ])


def step_cookies(cfg, fix):
    heading("3. Download quality (YouTube Premium cookies)")
    browser = cfg.get("cookies_browser", "")

    if not browser and fix:
        note("Without a login YouTube serves ~128 kbps. With a YouTube Premium\n"
             "login it serves ~256 kbps AAC — the ceiling for this pipeline.")
        if ask_yes("Do you have YouTube Premium?", default=False):
            browser = ask_choice("Which browser are you logged into?",
                                 list(VALID_BROWSERS), "safari")
            cfg["cookies_browser"] = browser
            save_config(cfg)

    if not browser:
        report("info", "cookies off", "~128 kbps — `djdl config cookies safari` to change")
        return []

    report("ok", f"cookies from {browser}")

    if not tools.find_exe("deno"):
        report("warn", "deno missing", "YouTube's JS challenge won't solve without it")
        note("Fix: brew install deno   (or re-run `djdl setup` and say yes at step 1)")

    if not tools.IS_MACOS:
        return []

    if browser != "safari":
        data_dir = BROWSER_DATA_DIRS.get(browser)
        if data_dir and data_dir.exists():
            report("ok", f"{browser} profile found", str(data_dir))
        else:
            report("warn", f"no {browser} profile found", "is it installed and logged in?")
        return []

    state, _path = safari_cookie_access()
    if state == "ok":
        report("ok", "Safari cookie store is readable", "Full Disk Access looks granted")
    elif state == "missing":
        report("warn", "no Safari cookie file found", "log into YouTube in Safari first")
    else:
        app = terminal_app_name()
        report("bad", "cannot read Safari's cookies", f"{app} needs Full Disk Access")
        note(f"System Settings → Privacy & Security → Full Disk Access → add {app},\n"
             f"then fully quit and reopen {app} and run `djdl setup` again.")
        if fix and ask_yes("Open that settings pane now?", default=True):
            open_full_disk_access_pane()
        return ["Full Disk Access is off, so Premium cookies can't be read"]
    return []


# ---- 4. the xml ----------------------------------------------------------- #
def step_xml(cfg, fix):
    heading("4. rekordbox.xml")
    xml_path = Path(cfg["xml_path"])
    if xml_path.exists():
        report("ok", "xml exists", str(xml_path))
        return []

    report("bad", "xml not created yet", str(xml_path))
    # rekordbox's file picker can't select a file that doesn't exist, so make
    # one now even if the folder is still empty.
    if not fix:
        return ["rekordbox.xml doesn't exist yet — run `djdl setup`"]
    if not ask_yes("Create it now (empty is fine)?", default=True):
        return ["rekordbox.xml doesn't exist yet — rekordbox can't be pointed at it"]
    try:
        rbxml.generate(cfg)
    except OSError as e:
        report("bad", "could not write the xml", str(e))
        return [f"could not write {xml_path}: {e}"]
    return []


# ---- 5. the rekordbox link ------------------------------------------------ #
def _manual_steps(cfg, xml_path):
    note(rbsettings.SETUP_HELP.format(xml_path=xml_path,
                                      playlist_name=playlist_name(cfg)))


def step_rekordbox(cfg, fix):
    heading("5. The rekordbox link")
    xml_path = cfg["xml_path"]
    if Path(xml_path).exists():
        xml_path = str(Path(xml_path).resolve())

    if not tools.IS_MACOS:
        report("info", "not macOS", "set the preference by hand")
        _manual_steps(cfg, xml_path)
        return []

    found = rbsettings.settings_files()
    if not found:
        report("warn", "no rekordbox settings found", "install rekordbox and launch it once")
        note("Then run `djdl setup` again and it can wire the xml up for you.")
        return []

    settings = found[0]
    text = settings.read_text(encoding="utf-8", errors="replace")
    linked = rbsettings.read_setting(text, "bridgeImportedLibraryFile") or ""
    sidebar = rbsettings.read_setting(text, "showRbXml") or "0"
    linked_ok = bool(linked) and os.path.realpath(linked) == os.path.realpath(xml_path)

    if linked_ok:
        report("ok", "rekordbox points at your xml", linked)
    elif linked:
        report("bad", "rekordbox points somewhere else", linked)
    else:
        report("bad", "rekordbox has no xml library set")

    if sidebar == "1":
        report("ok", "the rekordbox xml node is shown in the sidebar")
    else:
        report("bad", "the rekordbox xml node is hidden in the sidebar")

    if linked_ok and sidebar == "1":
        return []

    updates = {}
    if not linked_ok:
        updates["bridgeImportedLibraryFile"] = xml_path
    if sidebar != "1":
        updates["showRbXml"] = "1"

    if not fix:
        note("Run `djdl setup` to have these written for you, or set them by hand:")
        _manual_steps(cfg, xml_path)
        return ["rekordbox is not pointed at your rekordbox.xml yet"]

    print()
    note(f"djdl can write these into {settings.name} for you:")
    for key, value in updates.items():
        note(f"  {key} = {value}")
    if not ask_yes("Write them?", default=True):
        note("Skipped. The manual steps are in `djdl setup-help`.")
        return ["rekordbox is not pointed at your rekordbox.xml yet"]

    # rekordbox rewrites this file when it quits, so it has to be closed first
    # or our edit gets clobbered.
    if rbsettings.is_running():
        report("warn", "rekordbox is running", "it overwrites its settings on quit")
        if not ask_yes("Quit rekordbox now?", default=True):
            note("Quit rekordbox and re-run `djdl setup`.")
            return ["rekordbox was running, so its settings were left alone"]
        if not rbsettings.quit_app():
            report("bad", "rekordbox didn't quit",
                   "quit it by hand, then re-run `djdl setup`")
            return ["rekordbox was still running, so its settings were left alone"]
        report("ok", "rekordbox quit")

    try:
        backup = rbsettings.write_settings(settings, updates)
    except OSError as e:
        report("bad", "could not write rekordbox settings", str(e))
        return [f"could not write {settings}: {e}"]
    report("ok", "rekordbox settings written", f"backup at {backup.name}")
    note("Start rekordbox — 'rekordbox xml' will be in the left sidebar.")
    return []


# ---- 6. live check -------------------------------------------------------- #
COOKIE_RE = re.compile(r"Extracted (\d+) cookies from")


def parse_probe(out):
    """(format_id, kbps, codec, cookies_loaded) from a probe run's output."""
    m = COOKIE_RE.search(out)
    cookies = int(m.group(1)) if m else 0
    line = next((l for l in out.strip().splitlines() if "|" in l), "")
    fmt, abr, codec = (line.split("|") + ["", ""])[:3] if line else ("", "", "")
    try:
        kbps = float(abr)
    except ValueError:
        kbps = 0.0
    return fmt, kbps, codec, cookies


def probe_verdict(browser, fmt, kbps, cookies):
    """(state, label, detail, advice) for what YouTube just offered us.

    The useful distinction is between a session that never loaded and one that
    loaded fine and still got the free stream — they have nothing in common, and
    blaming both on the same four things sends you chasing the wrong one.
    """
    detail = f"format {fmt}, ~{kbps:.0f} kbps"

    if not browser:
        return "ok", "free-tier quality confirmed", detail, (
            "Have Premium? `djdl config cookies safari` roughly doubles the bitrate.")

    if not cookies:
        return "warn", "cookies are configured but none were loaded", detail, (
            f"yt-dlp read no cookies from {browser}. On macOS that is normally\n"
            f"Full Disk Access (see step 3), or you are not logged in there.")

    if fmt == "141" or kbps >= 200:
        return "ok", "Premium quality confirmed", detail, ""

    return "warn", f"signed in ({cookies} cookies) but served the free stream", detail, (
        "The session loaded, so this is not Full Disk Access and not your cookies.\n"
        "YouTube simply did not offer format 141 (256k AAC). That means either:\n"
        "  · the Google account has no active YouTube Premium subscription, or\n"
        "  · YouTube changed how it gates 141 — this happens every few weeks and\n"
        "    is fixed by a later yt-dlp release, not by anything you can change.\n"
        "Check `yt-dlp -F <url>` for a 141 row to tell them apart.\n"
        "Downloads still work, just at ~128 kbps.")


def step_probe(cfg, fix):
    """Read-only end-to-end check: ask YouTube what it would hand us."""
    if not fix:
        return []
    heading("6. Live check")
    if not ask_yes("Ask YouTube what quality it would serve? (no download)", default=True):
        return []

    exe = tools.find_exe("yt-dlp")
    if not exe:
        return []
    # --no-quiet, and no --no-warnings: the "Extracted N cookies" line is the
    # only way to tell a session that failed to load from one that loaded and
    # still got nothing, and --print otherwise implies --quiet and hides it.
    cmd = [exe, "--ignore-config", "--simulate", "--no-playlist", "--no-quiet",
           "-f", "141/bestaudio[ext=m4a]/bestaudio",
           "--print", "%(format_id)s|%(abr)s|%(acodec)s", PROBE_URL]
    browser = cfg.get("cookies_browser", "")
    if browser:
        cmd += ["--cookies-from-browser", browser]

    print(paint("    probing…", "90"))
    rc, out = tools.run_quiet(cmd, timeout=120)
    fmt, kbps, codec, cookies = parse_probe(out)
    if rc != 0 or not fmt:
        report("bad", "the probe failed")
        if "Operation not permitted" in out:
            note(f"Full Disk Access is off for {terminal_app_name()} — see step 3.")
        elif "Only images are available" in out:
            note("That's the missing-deno symptom: brew install deno")
        else:
            note((out.strip().splitlines() or ["no output"])[-1][:300])
        return ["the live quality check failed"]

    state, label, detail, advice = probe_verdict(browser, fmt, kbps, cookies)
    report(state, label, f"{detail}, {codec}" if codec else detail)
    if advice:
        note(advice)
    return []


# ---- the run itself ------------------------------------------------------- #
def finish(blockers, cfg):
    heading("Summary")
    if blockers:
        for item in blockers:
            report("bad", item)
        note("Fix those and run `djdl setup` again.")
        return 1

    report("ok", "everything checks out")
    if cfg:
        note(f"Paste a link to get going:  djdl https://youtube.com/watch?v=…\n"
             f"Tracks land in {cfg['music_dir']}\n"
             f"After each download, hit refresh on the 'rekordbox xml' node in\n"
             f"rekordbox, open the '{playlist_name(cfg)}' playlist, "
             f"select all → Import to Collection.")
    return 0


def run(fix=True):
    title(f"djdl {'setup' if fix else 'doctor'} — checking everything end to end")
    if fix and not interactive():
        print(paint("  (not a terminal — running in read-only check mode)", "90"))
        fix = False

    blockers = step_tools(fix)
    cfg, config_blockers = step_config(fix)
    blockers += config_blockers
    if config_blockers:
        # Everything below needs a usable music folder.
        return finish(blockers, None)

    for step in (step_cookies, step_xml, step_rekordbox, step_probe):
        blockers += step(cfg, fix)
    return finish(blockers, cfg)
