"""Turns one day of raw records into a short, cleaned-up summary.

This is the privacy step. The raw records (every window title, every web
address) stay on the laptop. The summary keeps details only for groups
marked "full" in categories.toml; everything else becomes a time total.

Only this summary is ever shown to the brain.

Try it:  python3 -m digest.make_digest 2026-11-15
"""

import json
import re
import sys
import tomllib
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from shared.settings import DIGESTS, PRIVATE, RECORDS, WINDOW_RECORDS, load_settings, make_private_folders
from digest.sort_with_local_model import sort_unknown
from watchers.browser_history import visits_on
from watchers.claude_code_sessions import sessions_on
from watchers.git_commits import commits_on
from watchers.notion_pages import tracker_rows_on

BROWSERS = ("firefox", "chromium", "chrome", "brave")
BROWSER_NAME_IN_TITLE = re.compile(r"\s+[—–-]\s+(Mozilla Firefox|Chromium|Google Chrome|Brave)( Private Browsing)?$")
UNREAD_COUNT_IN_TITLE = re.compile(r"^\(\d+\+?\)\s+")

MOST_DETAILS_PER_GROUP = 8
SHORTEST_DETAIL_WORTH_LISTING = 120   # seconds
LONGEST_TITLE = 90
MOST_TRACKER_ROWS = 15


# ---------- sorting activity into groups ----------

def load_categories() -> dict:
    groups = tomllib.loads((Path(__file__).parent / "categories.toml").read_text())
    mine = PRIVATE / "my_categories.toml"
    if mine.exists():
        for name, extra in tomllib.loads(mine.read_text()).items():
            group = groups.setdefault(name, {"detail": "totals"})
            group["detail"] = extra.get("detail", group["detail"])
            for kind in ("apps", "sites", "words"):
                group[kind] = group.get(kind, []) + extra.get(kind, [])
    return groups


def site_matches(site: str, rule: str) -> bool:
    return site == rule or site.endswith("." + rule)


def group_for(groups: dict, app: str, title: str, site: str) -> str:
    """The first group whose rules match this app, page or title."""
    low_title = title.lower()
    for name, rules in groups.items():
        if site and any(site_matches(site, rule) for rule in rules.get("sites", [])):
            return name
        if any(word in low_title for word in rules.get("words", [])):
            return name
        if not site and any(part in app for part in rules.get("apps", [])):
            return name
    return "other"


def clean_title(title: str) -> str:
    title = BROWSER_NAME_IN_TITLE.sub("", title)
    title = UNREAD_COUNT_IN_TITLE.sub("", title)
    return title.strip()[:LONGEST_TITLE]


def as_hours(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes // 60}h{minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


# ---------- reading the day's raw records ----------

def window_notes_on(day: date) -> list[dict]:
    file = WINDOW_RECORDS / f"{day}.jsonl"
    if not file.exists():
        return []
    notes = []
    for line in file.read_text().splitlines():
        try:
            notes.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return notes


# ---------- building the summary ----------

def time_at_laptop(notes: list[dict], settings: dict, groups: dict, page_sites: dict) -> tuple[list[str], dict]:
    """Lines about where my screen time went, plus what could not be sorted."""
    here = [note for note in notes if not note["away"]]
    if not here:
        return [], {}
    seconds_each = settings["seconds_between_window_checks"]

    # First pass: sort every note with the written rules.
    sorted_notes = []
    unknown_example: dict[str, str] = {}
    unknown_time: dict[str, float] = defaultdict(float)
    for note in here:
        is_browser = any(name in note["app"] for name in BROWSERS)
        title = clean_title(note["title"])
        site = page_sites.get(title, "") if is_browser else ""
        if is_browser and title == "Jarvis":
            group = "talking_to_jarvis"
        else:
            group = group_for(groups, note["app"], title, site)
        name = site or note["app"]
        if group == "other":
            unknown_example.setdefault(name, title)
            unknown_time[name] += seconds_each
        sorted_notes.append((note, title, name, group))

    # Second pass: let the local model sort what the rules did not recognise.
    by_local_model: dict[str, str] = {}
    if settings.get("sort_unknown_with_local_model"):
        worth_asking = {
            name: unknown_example[name] for name, seconds in unknown_time.items()
            if seconds >= SHORTEST_DETAIL_WORTH_LISTING
        }
        by_local_model = sort_unknown(worth_asking, groups)

    time_in_group: dict[str, float] = defaultdict(float)
    time_on_detail: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    hours_active = set()
    not_sorted: dict[str, float] = defaultdict(float)

    for note, title, name, group in sorted_notes:
        hours_active.add(int(note["time"][11:13]))
        if group == "other":
            # Sorted by the local model: counts toward the time total only, titles are not kept.
            group = by_local_model.get(name, "other")
            if group == "other":
                not_sorted[name] += seconds_each
        else:
            time_on_detail[group][title or note["app"]] += seconds_each
        time_in_group[group] += seconds_each

    first, last = here[0]["time"][11:16], here[-1]["time"][11:16]
    lines = [
        f"At the laptop: {as_hours(len(here) * seconds_each)} (first activity {first}, last {last})",
        "Hours with activity: " + ", ".join(f"{hour:02d}" for hour in sorted(hours_active)),
        "",
        "## Where the time went",
    ]
    for group, seconds in sorted(time_in_group.items(), key=lambda pair: -pair[1]):
        detail = groups.get(group, {}).get("detail", "totals")
        if detail == "hidden":
            continue
        if detail != "full":
            lines.append(f"- {group}: {as_hours(seconds)} (details kept private)")
            continue
        lines.append(f"- {group}: {as_hours(seconds)}")
        biggest = sorted(time_on_detail[group].items(), key=lambda pair: -pair[1])[:MOST_DETAILS_PER_GROUP]
        for title, spent in biggest:
            if spent >= SHORTEST_DETAIL_WORTH_LISTING:
                lines.append(f"    - {as_hours(spent)}: {title}")
    return lines, not_sorted


def pages_visited(visits: list[dict], groups: dict) -> list[str]:
    """Used when there are no window notes for the day: counts page visits instead of time."""
    count_in_group: dict[str, int] = defaultdict(int)
    titles_in_group: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for visit in visits:
        title = clean_title(visit["title"])
        group = group_for(groups, "", title, visit["site"])
        count_in_group[group] += 1
        if title:
            titles_in_group[group][title] += 1

    lines = ["## Web pages opened (no screen-time record for this day)"]
    for group, count in sorted(count_in_group.items(), key=lambda pair: -pair[1]):
        detail = groups.get(group, {}).get("detail", "totals")
        if detail == "hidden":
            continue
        if detail != "full":
            lines.append(f"- {group}: {count} pages (details kept private)")
            continue
        lines.append(f"- {group}: {count} pages")
        for title, _ in sorted(titles_in_group[group].items(), key=lambda pair: -pair[1])[:MOST_DETAILS_PER_GROUP]:
            lines.append(f"    - {title}")
    return lines


def make_digest(day: date) -> str:
    """The cleaned summary of one day, as text."""
    settings = load_settings()
    groups = load_categories()
    notes = window_notes_on(day)
    visits = visits_on(day)
    page_sites = {clean_title(visit["title"]): visit["site"] for visit in visits if visit["title"]}

    lines = [f"# {day:%A %d %B %Y}", ""]

    screen_lines, not_sorted = time_at_laptop(notes, settings, groups, page_sites)
    if screen_lines:
        lines += screen_lines
    elif visits:
        lines += pages_visited(visits, groups)
    else:
        lines.append("No laptop activity recorded.")

    sessions = sessions_on(day)
    lines += ["", "## Claude Code"]
    if not sessions:
        lines.append("- Not used.")
    for entry in sessions:
        topics = "; ".join(entry["topics"][:3])
        lines.append(
            f"- {entry['project']}: {entry['sessions']} session(s), about {entry['minutes']} min of back-and-forth, "
            f"{entry['first']:%H:%M} to {entry['last']:%H:%M}" + (f". Topics: {topics}" if topics else "")
        )

    commits = commits_on(day)
    lines += ["", "## Code saved (git commits)"]
    if not commits:
        lines.append("- None.")
    for entry in commits:
        lines.append(f"- {entry['project']}: {entry['commits']} commit(s)")
        for message in entry["messages"][:5]:
            lines.append(f"    - {message[:LONGEST_TITLE]}")

    rows = tracker_rows_on(day)
    if rows:
        lines += ["", "## What I logged in my Notion trackers"]
        for row in rows[:MOST_TRACKER_ROWS]:
            lines.append(f"- {row['tracker']}: {row['text'][:300]}")

    if not_sorted:
        save_not_sorted(day, not_sorted)
    return "\n".join(lines) + "\n"


def save_not_sorted(day: date, not_sorted: dict) -> None:
    """A local-only list of apps and sites that matched no group, so I can add rules for them."""
    lines = [f"# Not sorted into any group on {day}", "",
             "Add rules for these in private/my_categories.toml. This file never leaves the laptop.", ""]
    for name, seconds in sorted(not_sorted.items(), key=lambda pair: -pair[1]):
        lines.append(f"- {as_hours(seconds)}: {name}")
    (RECORDS / "not_sorted_yet.md").write_text("\n".join(lines) + "\n")


def digest_for(day: date, redo: bool = False) -> str:
    """Past days are made once and kept. Today is always made fresh."""
    make_private_folders()
    file = DIGESTS / f"{day}.md"
    if file.exists() and day < date.today() and not redo:
        return file.read_text()
    text = make_digest(day)
    if day < date.today():
        file.write_text(text)
    return text


def recent_digests(days: int) -> str:
    """The last few days, oldest first, ending with today so far."""
    today = date.today()
    parts = [digest_for(today - timedelta(days=back)) for back in range(days, 0, -1)]
    parts.append(digest_for(today).replace("\n", f"  (today so far, as of {datetime.now():%H:%M})\n", 1))
    return "\n".join(parts)


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(digest_for(day, redo=True))
