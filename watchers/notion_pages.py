"""Copies my Notion pages and trackers onto this laptop so Jarvis can read them.

Notion only shows this script the pages I have shared with it, so I choose
what Jarvis can see. Setting it up is described in the README under
"Connecting Notion". The key goes in private/settings.toml:

    notion_key = "secret_..."

What it saves, all inside private/:

    private/context/notion/<page>.md      one file per page, starting with the date it was last edited
    private/context/notion/<tracker>.md   one file per tracker (database), recent rows only
    private/records/notion_rows.json      recent tracker rows, used in the daily summary

Old material is handled on purpose:
- a page not edited for a long time (old_after_days in settings.toml) is
  saved only as a short opening, enough for Jarvis to know it exists;
- a tracker keeps only its recent rows, plus a count of the older ones.

Run it:  python3 -m watchers.notion_pages     (or: jarvis notion)
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from shared.settings import CONTEXT, RECORDS, load_settings, make_private_folders

NOTION = "https://api.notion.com/v1"
NOTION_FOLDER = CONTEXT / "notion"
ALREADY_FETCHED = NOTION_FOLDER / ".fetched.json"
ROWS_FOR_DIGEST = RECORDS / "notion_rows.json"

PAUSE_BETWEEN_REQUESTS = 0.35     # Notion allows about three requests a second
HOW_DEEP_INTO_A_PAGE = 2          # lists inside lists inside lists
OPENING_OF_AN_OLD_PAGE = 1500     # characters kept from a page that counts as old
MOST_RECENT_ROWS = 200


class NotionProblem(Exception):
    pass


def ask_notion(key: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        NOTION + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    time.sleep(PAUSE_BETWEEN_REQUESTS)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as problem:
        detail = problem.read().decode(errors="ignore")[:200]
        raise NotionProblem(f"Notion said no ({problem.code}): {detail}") from problem
    except OSError as problem:
        raise NotionProblem(f"Could not reach Notion: {problem}") from problem


def everything(key: str, path: str, body: dict | None = None) -> list[dict]:
    """Notion answers in pages of 100; keep asking until there is no more."""
    results, cursor = [], None
    while True:
        if body is None:
            answer = ask_notion(key, path + (f"&start_cursor={cursor}" if cursor else ""))
        else:
            answer = ask_notion(key, path, {**body, **({"start_cursor": cursor} if cursor else {})})
        results += answer.get("results", [])
        cursor = answer.get("next_cursor")
        if not answer.get("has_more") or not cursor:
            return results


# ---------- turning Notion's format into plain text ----------

def plain(rich_text: list[dict]) -> str:
    return "".join(piece.get("plain_text", "") for piece in rich_text or [])


def title_of(item: dict) -> str:
    if item.get("object") == "database":
        return plain(item.get("title")) or "Untitled tracker"
    for value in item.get("properties", {}).values():
        if value.get("type") == "title":
            return plain(value.get("title")) or "Untitled"
    return "Untitled"


def value_as_text(value: dict) -> str:
    """One cell of a tracker row, as text."""
    kind = value.get("type")
    inside = value.get(kind)
    if inside is None or inside == [] or inside == "":
        return ""
    if kind in ("title", "rich_text"):
        return plain(inside)
    if kind in ("number", "url", "email", "phone_number"):
        return str(inside)
    if kind == "checkbox":
        return "yes" if inside else "no"
    if kind in ("select", "status"):
        return inside.get("name", "")
    if kind == "multi_select":
        return ", ".join(choice.get("name", "") for choice in inside)
    if kind == "date":
        return inside.get("start", "") + (f" to {inside['end']}" if inside.get("end") else "")
    if kind == "formula":
        return str(inside.get(inside.get("type"), "") or "")
    if kind in ("created_time", "last_edited_time"):
        return str(inside)[:10]
    if kind == "relation":
        return f"{len(inside)} linked"
    return ""


def row_as_text(row: dict) -> str:
    cells = []
    for name, value in row.get("properties", {}).items():
        text = value_as_text(value).strip()
        if text:
            cells.append(f"{name}: {text[:200]}")
    return " | ".join(cells)


def block_as_text(block: dict) -> str:
    kind = block.get("type", "")
    inside = block.get(kind, {})
    text = plain(inside.get("rich_text")) if isinstance(inside, dict) else ""
    if kind.startswith("heading_"):
        return "#" * int(kind[-1]) + " " + text
    if kind in ("bulleted_list_item", "numbered_list_item", "toggle"):
        return "- " + text
    if kind == "to_do":
        return ("- [x] " if inside.get("checked") else "- [ ] ") + text
    if kind == "quote":
        return "> " + text
    return text


def page_text(key: str, block_id: str, depth: int = 0, whole_page: bool = True) -> str:
    """The words on a page. For an old page only the opening is read."""
    if whole_page:
        blocks = everything(key, f"/blocks/{block_id}/children?page_size=100")
    else:
        blocks = ask_notion(key, f"/blocks/{block_id}/children?page_size=50").get("results", [])
    lines = []
    for block in blocks:
        text = block_as_text(block)
        if text.strip():
            lines.append("  " * depth + text)
        nested = block.get("has_children") and block.get("type") not in ("child_page", "child_database")
        if nested and whole_page and depth < HOW_DEEP_INTO_A_PAGE:
            lines.append(page_text(key, block["id"], depth + 1))
    return "\n".join(line for line in lines if line)


# ---------- saving ----------

def file_name(title: str, notion_id: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50] or "untitled"
    return f"{safe}_{notion_id.replace('-', '')[:6]}.md"


def edited_day(item: dict) -> date:
    return datetime.fromisoformat(item["last_edited_time"].replace("Z", "+00:00")).astimezone().date()


def save_page(key: str, page: dict, old_before: date) -> None:
    title, edited = title_of(page), edited_day(page)
    is_old = edited < old_before
    text = page_text(key, page["id"], whole_page=not is_old)
    if is_old and len(text) > OPENING_OF_AN_OLD_PAGE:
        text = text[:OPENING_OF_AN_OLD_PAGE] + "\n[Only the opening was copied because this page is old.]"
    (NOTION_FOLDER / file_name(title, page["id"])).write_text(
        f'Source: Notion page "{title}"\nLast edited: {edited}\n\n{text}\n'
    )


def save_tracker(key: str, tracker: dict, old_before: date) -> list[dict]:
    """Save a tracker's recent rows. Returns them for the daily summary."""
    title = title_of(tracker)
    rows = everything(key, f"/databases/{tracker['id']}/query", {
        "page_size": 100,
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
    })
    if not rows:
        return []
    days = [edited_day(row) for row in rows]
    recent = [(day, row_as_text(row)) for day, row in zip(days, rows) if day >= old_before][:MOST_RECENT_ROWS]
    older = len(rows) - len(recent)

    lines = [
        f'Source: Notion tracker "{title}"',
        f"Last edited: {max(days)}",
        f"Rows: {len(rows)} in total, last edited between {min(days)} and {max(days)}.",
        "",
    ]
    if recent:
        lines.append("Recent rows (newest first):")
        lines += [f"- {day} | {text}" for day, text in recent if text]
    else:
        lines.append("No recent rows. This tracker looks like it is no longer used.")
    if older:
        lines.append(f"\n{older} older row(s) were not copied.")
    (NOTION_FOLDER / file_name(title, tracker["id"])).write_text("\n".join(lines) + "\n")
    return [{"tracker": title, "day": str(day), "text": text} for day, text in recent if text]


def fetch_notion() -> bool:
    """Copy what changed since last time. Returns False when no key is set."""
    settings = load_settings()
    key = settings.get("notion_key", "")
    if not key:
        return False
    make_private_folders()
    NOTION_FOLDER.mkdir(parents=True, exist_ok=True)
    fetched = json.loads(ALREADY_FETCHED.read_text()) if ALREADY_FETCHED.exists() else {}
    old_before = date.today() - timedelta(days=settings["old_after_days"])

    pages = everything(key, "/search", {"page_size": 100, "filter": {"property": "object", "value": "page"}})
    trackers = everything(key, "/search", {"page_size": 100, "filter": {"property": "object", "value": "database"}})

    copied = 0
    for page in pages:
        if page.get("parent", {}).get("type") == "database_id":
            continue      # a tracker row; handled with its tracker below
        if fetched.get(page["id"]) == page["last_edited_time"]:
            continue      # not changed since last time
        save_page(key, page, old_before)
        fetched[page["id"]] = page["last_edited_time"]
        copied += 1

    rows_for_digest = []
    for tracker in trackers:
        rows_for_digest += save_tracker(key, tracker, old_before)

    ALREADY_FETCHED.write_text(json.dumps(fetched, indent=1))
    ROWS_FOR_DIGEST.write_text(json.dumps(rows_for_digest, indent=1, ensure_ascii=False))
    print(f"Notion: copied {copied} new or changed page(s) and {len(trackers)} tracker(s).")
    return True


def tracker_rows_on(day: date) -> list[dict]:
    """Tracker rows I added or changed on that day (from the last fetch)."""
    if not ROWS_FOR_DIGEST.exists():
        return []
    return [row for row in json.loads(ROWS_FOR_DIGEST.read_text()) if row["day"] == str(day)]


if __name__ == "__main__":
    try:
        if not fetch_notion():
            print('No Notion key yet. Add  notion_key = "secret_..."  to private/settings.toml '
                  "(see README, Connecting Notion).")
            sys.exit(1)
    except NotionProblem as problem:
        print(problem)
        sys.exit(1)
