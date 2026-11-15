"""Reads when and where I used Claude Code on a given day.

Claude Code already saves every session under ~/.claude/projects.
This only reads those files. Nothing here leaves the laptop.

Try it:  python3 -m watchers.claude_code_sessions 2026-11-15
"""

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SESSIONS = Path.home() / ".claude" / "projects"

# Two messages further apart than this count as a break, not as working time.
LONGEST_PAUSE = timedelta(minutes=10)

# Text that Claude Code adds to my messages by itself. Not something I typed.
AUTOMATIC_TEXT = re.compile(
    r"<(system-reminder|local-command-[a-z]+|command-[a-z]+|task-notification)>.*?</\1>", re.DOTALL
)


def what_i_typed(line: dict) -> str | None:
    """The text of a message I typed myself (not automatic ones)."""
    if line.get("type") != "user" or line.get("isMeta") or line.get("isSidechain"):
        return None
    content = line.get("message", {}).get("content")
    if isinstance(content, list):
        content = " ".join(part.get("text", "") for part in content if part.get("type") == "text")
    if not isinstance(content, str):
        return None
    content = AUTOMATIC_TEXT.sub("", content).strip()
    return content or None


def read_session(file: Path) -> list[dict]:
    lines = []
    with file.open(errors="ignore") as session:
        for raw in session:
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return lines


def local_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


def sessions_on(day: date) -> list[dict]:
    """One entry per project I worked on that day."""
    by_project: dict[str, dict] = {}

    for file in SESSIONS.glob("*/*.jsonl"):
        # Skip files last changed before that day: nothing in them can match.
        if date.fromtimestamp(file.stat().st_mtime) < day:
            continue

        times, typed, title, project = [], 0, "", ""
        for line in read_session(file):
            if line.get("type") == "ai-title":
                title = line.get("aiTitle") or line.get("title") or title
            stamp = line.get("timestamp")
            if not stamp or local_time(stamp).date() != day:
                continue
            project = project or Path(line.get("cwd") or "").name
            if line.get("type") in ("user", "assistant"):
                times.append(local_time(stamp))
            if what_i_typed(line):
                typed += 1

        if not times or not typed:
            continue
        times.sort()
        working = sum(
            (later - earlier for earlier, later in zip(times, times[1:]) if later - earlier <= LONGEST_PAUSE),
            timedelta(),
        )
        entry = by_project.setdefault(
            project or "unknown",
            {"project": project or "unknown", "sessions": 0, "messages_i_typed": 0,
             "minutes": 0, "first": times[0], "last": times[-1], "topics": []},
        )
        entry["sessions"] += 1
        entry["messages_i_typed"] += typed
        entry["minutes"] += round(working.total_seconds() / 60)
        entry["first"] = min(entry["first"], times[0])
        entry["last"] = max(entry["last"], times[-1])
        if title:
            entry["topics"].append(title)

    return sorted(by_project.values(), key=lambda entry: entry["first"])


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    for entry in sessions_on(day):
        print(f"{entry['project']}: {entry['sessions']} session(s), {entry['minutes']} min, "
              f"{entry['first']:%H:%M}-{entry['last']:%H:%M}, topics: {entry['topics']}")
