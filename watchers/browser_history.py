"""Reads which web pages I visited on a given day, from Firefox and Chromium.

The browsers already keep this history on disk; this only reads it.
Nothing here leaves the laptop.

Try it:  python3 -m watchers.browser_history 2026-11-15
"""

import shutil
import sqlite3
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
FIREFOX_FILES = [
    *HOME.glob("snap/firefox/common/.mozilla/firefox/*/places.sqlite"),
    *HOME.glob(".mozilla/firefox/*/places.sqlite"),
]
CHROMIUM_FILES = [
    *HOME.glob("snap/chromium/common/chromium/*/History"),
    *HOME.glob(".config/chromium/*/History"),
    *HOME.glob(".config/google-chrome/*/History"),
]

# Chromium counts time in microseconds since the year 1601.
CHROMIUM_YEAR_ZERO = datetime(1601, 1, 1)


def read_copy(history_file: Path, question: str, values: tuple) -> list[tuple]:
    """The browser locks its history while open, so read a temporary copy."""
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "history"
        try:
            shutil.copy(history_file, copy)
            for extra in ("-wal", "-shm"):
                side_file = Path(str(history_file) + extra)
                if side_file.exists():
                    shutil.copy(side_file, str(copy) + extra)
            with sqlite3.connect(copy) as database:
                return database.execute(question, values).fetchall()
        except (sqlite3.Error, OSError):
            return []


def site_of(address: str) -> str:
    site = urlparse(address).netloc.lower()
    return site.removeprefix("www.")


def visits_on(day: date) -> list[dict]:
    """Every page visit on that day: time, site, page title."""
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    visits = []

    for file in FIREFOX_FILES:
        rows = read_copy(
            file,
            "SELECT v.visit_date, p.url, p.title FROM moz_historyvisits v "
            "JOIN moz_places p ON p.id = v.place_id WHERE v.visit_date BETWEEN ? AND ?",
            (int(start.timestamp() * 1_000_000), int(end.timestamp() * 1_000_000)),
        )
        for when, address, title in rows:
            visits.append({
                "time": datetime.fromtimestamp(when / 1_000_000).isoformat(timespec="seconds"),
                "site": site_of(address),
                "title": title or "",
            })

    for file in CHROMIUM_FILES:
        # Chromium stores times in UTC.
        utc_gap = datetime.now().astimezone().utcoffset()
        since = int((start - utc_gap - CHROMIUM_YEAR_ZERO).total_seconds() * 1_000_000)
        until = int((end - utc_gap - CHROMIUM_YEAR_ZERO).total_seconds() * 1_000_000)
        rows = read_copy(
            file,
            "SELECT v.visit_time, u.url, u.title FROM visits v "
            "JOIN urls u ON u.id = v.url WHERE v.visit_time BETWEEN ? AND ?",
            (since, until),
        )
        for when, address, title in rows:
            local = CHROMIUM_YEAR_ZERO + timedelta(microseconds=when) + utc_gap
            visits.append({
                "time": local.isoformat(timespec="seconds"),
                "site": site_of(address),
                "title": title or "",
            })

    return sorted((v for v in visits if v["site"]), key=lambda v: v["time"])


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    found = visits_on(day)
    print(f"{len(found)} page visits on {day}")
    sites: dict[str, int] = {}
    for visit in found:
        sites[visit["site"]] = sites.get(visit["site"], 0) + 1
    for site, count in sorted(sites.items(), key=lambda pair: -pair[1])[:10]:
        print(f"  {count:4}  {site}")
