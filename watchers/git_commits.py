"""Reads which code changes I saved (git commits) on a given day.

Looks through my code folders for git projects and asks each one
what I committed. Nothing here leaves the laptop.

Try it:  python3 -m watchers.git_commits 2026-11-15
"""

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from shared.settings import load_settings

FOLDERS_TO_SKIP = {"node_modules", "snap", "venv", "build", "install", "log", "__pycache__", "site-packages"}
HOW_DEEP_TO_LOOK = 4


def find_projects(start_folders: list[str]) -> list[Path]:
    """Every folder that is a git project, a few levels deep."""
    projects = []
    for start in start_folders:
        top = Path(start).expanduser()
        for folder, inside, _files in os.walk(top):
            depth = len(Path(folder).relative_to(top).parts)
            if ".git" in inside:
                projects.append(Path(folder))
            inside[:] = [
                name for name in inside
                if not name.startswith(".") and name not in FOLDERS_TO_SKIP and depth < HOW_DEEP_TO_LOOK
            ]
    return projects


def name_of(project: Path) -> str:
    """A readable name, for example 'robot/src' instead of just 'src'."""
    try:
        return str(project.relative_to(Path.home()))
    except ValueError:
        return project.name


def git(project: Path, *words: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(project), *words], capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def commits_on(day: date) -> list[dict]:
    """One entry per project that I committed to that day."""
    settings = load_settings()
    found = []
    for project in find_projects(settings["folders_with_my_code"]):
        me = git(project, "config", "user.email")
        if not me:
            continue
        log = git(
            project, "log", "--all", "--no-merges", f"--author={me}",
            f"--since={day} 00:00", f"--until={day + timedelta(days=1)} 00:00",
            "--format=%s",
        )
        messages = [line for line in log.splitlines() if line]
        if messages:
            found.append({"project": name_of(project), "commits": len(messages), "messages": messages})
    return found


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    for entry in commits_on(day):
        print(f"{entry['project']}: {entry['commits']} commit(s)")
        for message in entry["messages"]:
            print(f"    {message}")
