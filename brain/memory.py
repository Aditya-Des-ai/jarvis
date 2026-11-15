"""What Jarvis knows about me, kept as plain text notes in private/memory/.

    about_me.md              who I am and how I think
    areas/<name>.md          one note per area of my life (research, fitness, ...)
    decisions.md             decisions I made and my reasons, so Jarvis learns how I think
    corrections.md           times Jarvis guessed wrong and what the real reason was
    things_to_bring_up.md    things Jarvis wants to raise with me later
    past.md                  goals and views I used to hold (only read in deep mode)
    archive/                 what the weekly tidy moved out; never deleted, never read

The brain cannot write files. Instead it puts tags like this in its reply:

    <remember file="areas/fitness.md">Wants to lift 3 times a week.</remember>

and this code adds that line, with today's date, to the right note.
"""

import re
from datetime import date

from shared.settings import MEMORY, make_private_folders

REMEMBER_TAG = re.compile(r'<remember file="([^"]+)">(.*?)</remember>', re.DOTALL)
ALLOWED_NOTE_NAME = re.compile(r"^(areas/)?[a-z0-9_]+\.md$")
INTERVIEW_FINISHED_TAG = "<interview_finished/>"


# Notes that are not read on every message.
HISTORY_NOTE = "past.md"          # old goals and views; only read in deep mode
NOT_FOR_THE_BRAIN = {"tidy_log.md"}


def notes(include_past: bool = False) -> list:
    """The notes the brain reads. The archive folder is never among them."""
    make_private_folders()
    found = sorted(MEMORY.glob("*.md")) + sorted((MEMORY / "areas").glob("*.md"))
    return [
        note for note in found
        if note.name not in NOT_FOR_THE_BRAIN and (include_past or note.name != HISTORY_NOTE)
    ]


def read_memory(include_past: bool = False) -> str:
    """The notes joined into one text for the brain to read."""
    parts = [
        f"----- note: {note.relative_to(MEMORY)} -----\n{note.read_text().strip()}\n"
        for note in notes(include_past)
    ]
    return "\n".join(parts) or "(No notes yet.)"


def interview_finished() -> bool:
    return (MEMORY / "interview_finished").exists()


def save_what_to_remember(reply: str) -> str:
    """Store every <remember> tag in the reply, and return the reply without the tags."""
    make_private_folders()
    for name, text in REMEMBER_TAG.findall(reply):
        name, text = name.strip(), text.strip()
        if not text or not ALLOWED_NOTE_NAME.match(name):
            continue   # only plain note names inside private/memory are accepted
        note = MEMORY / name
        if not note.exists():
            title = note.stem.replace("_", " ").capitalize()
            note.write_text(f"# {title}\n")
        with note.open("a") as file:
            file.write(f"\n[{date.today()}] {text}\n")

    if INTERVIEW_FINISHED_TAG in reply:
        (MEMORY / "interview_finished").write_text(f"{date.today()}\n")

    reply = REMEMBER_TAG.sub("", reply).replace(INTERVIEW_FINISHED_TAG, "")
    return re.sub(r"\n{3,}", "\n\n", reply).strip()
