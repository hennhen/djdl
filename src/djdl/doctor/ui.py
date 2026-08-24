"""Terminal output and prompts for the setup/doctor run."""

import os
import sys

MARKS = {
    "ok": ("✓", "32"),
    "warn": ("!", "33"),
    "bad": ("✗", "31"),
    "info": ("·", "90"),
}


def use_color():
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if use_color() else text


def title(text):
    print(paint(f"\n{text}", "1"))


def heading(text):
    print("\n" + paint(text, "1;36"))


def report(state, label, detail=""):
    line = f"  {paint(*MARKS[state])} {label}"
    if detail:
        line += paint(f" — {detail}", "90")
    print(line)


def note(text):
    for line in text.strip("\n").split("\n"):
        print(paint(f"    {line}", "90"))


def interactive():
    return sys.stdin.isatty()


def ask_yes(prompt, default=True):
    """Ask a yes/no question. Non-interactive runs never assume a fix is wanted."""
    if not interactive():
        return False
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"    {paint('?', '35')} {prompt} {suffix} ").strip().lower()
        except EOFError:
            print()
            return default
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def ask_text(prompt, default=""):
    if not interactive():
        return default
    shown = f" [{default}]" if default else ""
    try:
        answer = input(f"    {paint('?', '35')} {prompt}{shown}: ").strip()
    except EOFError:
        print()
        return default
    return answer or default


def ask_choice(prompt, choices, default):
    if not interactive():
        return default
    while True:
        answer = ask_text(f"{prompt} ({'/'.join(choices)})", default).lower()
        if answer in choices:
            return answer
        print(paint(f"      pick one of: {', '.join(choices)}", "31"))
