"""The conversation between me and Jarvis, saved in private/chat/history.jsonl.

One line per message:  {"time": "...", "who": "me" or "jarvis", "text": "..."}
"""

import json
import threading
from datetime import datetime

from shared.settings import CHAT, make_private_folders

HISTORY = CHAT / "history.jsonl"
one_at_a_time = threading.Lock()


def add_message(who: str, text: str) -> dict:
    make_private_folders()
    message = {"time": datetime.now().isoformat(timespec="seconds"), "who": who, "text": text}
    with one_at_a_time, HISTORY.open("a") as file:
        file.write(json.dumps(message, ensure_ascii=False) + "\n")
    return message


def all_messages() -> list[dict]:
    if not HISTORY.exists():
        return []
    messages = []
    for line in HISTORY.read_text().splitlines():
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return messages


def as_text(messages: list[dict]) -> str:
    """The conversation written out for the brain to read."""
    lines = []
    for message in messages:
        when = datetime.fromisoformat(message["time"])
        name = "Me" if message["who"] == "me" else "Jarvis"
        lines.append(f"[{when:%d %b %H:%M}] {name}: {message['text']}")
    return "\n\n".join(lines) or "(Nothing said yet.)"
