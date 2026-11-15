"""Notes which window I'm looking at, every few seconds.

Runs all day in the background. Each check adds one line to
private/records/windows/<date>.jsonl, for example:

    {"time": "2026-11-15T10:42:30", "app": "code", "title": "notes.py - my_project", "away": false}

Nothing here leaves the laptop.

Run it:  python3 -m watchers.window_watcher
"""

import json
import re
import subprocess
import time
from datetime import datetime

from shared.settings import WINDOW_RECORDS, load_settings, make_private_folders

# Even with a video playing full screen, stop counting after this long without input.
LONGEST_FULLSCREEN_WITHOUT_INPUT = 3 * 60 * 60


def run(command: list[str]) -> str:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=5).stdout
    except (subprocess.SubprocessError, OSError):
        return ""


def focused_window() -> dict | None:
    """The app name, title and full-screen state of the window in front."""
    found = re.search(r"window id # (0x[0-9a-f]+)", run(["xprop", "-root", "_NET_ACTIVE_WINDOW"]))
    if not found or found.group(1) == "0x0":
        return None
    details = run(["xprop", "-id", found.group(1), "WM_CLASS", "_NET_WM_NAME", "_NET_WM_STATE"])

    app = re.search(r'WM_CLASS\(STRING\) = "[^"]*", "([^"]*)"', details)
    title = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"', details)
    return {
        "app": app.group(1).lower() if app else "unknown",
        "title": title.group(1).replace('\\"', '"') if title else "",
        "fullscreen": "_NET_WM_STATE_FULLSCREEN" in details,
    }


def seconds_since_last_input() -> float:
    """How long since I last touched the keyboard or mouse."""
    answer = run([
        "gdbus", "call", "--session",
        "--dest", "org.gnome.Mutter.IdleMonitor",
        "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
        "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime",
    ])
    found = re.search(r"uint64 (\d+)", answer)
    return int(found.group(1)) / 1000 if found else 0.0


def hide_private_browsing(window: dict) -> dict:
    """Private browser windows are recorded as time only, never by title."""
    if "private browsing" in window["title"].lower() or "(incognito)" in window["title"].lower():
        window["title"] = "[private window]"
    return window


def take_one_note(away_after: float) -> dict | None:
    window = focused_window()
    if window is None:
        return None
    window = hide_private_browsing(window)
    quiet_for = seconds_since_last_input()

    # Watching a full-screen video means no typing, but I'm still there.
    watching = window["fullscreen"] and quiet_for < LONGEST_FULLSCREEN_WITHOUT_INPUT
    away = quiet_for > away_after and not watching

    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "app": window["app"],
        "title": window["title"],
        "away": away,
    }


def main() -> None:
    settings = load_settings()
    make_private_folders()
    wait = settings["seconds_between_window_checks"]

    while True:
        note = take_one_note(settings["away_after_seconds"])
        if note:
            today = WINDOW_RECORDS / f"{note['time'][:10]}.jsonl"
            with today.open("a") as file:
                file.write(json.dumps(note, ensure_ascii=False) + "\n")
        time.sleep(wait)


if __name__ == "__main__":
    main()
