"""What Jarvis knows about me, kept as plain text notes in private/memory/.

    about_me.md              who I am and how I think
    areas/<name>.md          one note per area of my life (research, fitness, ...)
    decisions.md             decisions I made and my reasons, so Jarvis learns how I think
    corrections.md           times Jarvis guessed wrong and what the real reason was
    things_to_bring_up.md    things Jarvis wants to raise with me later

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


def read_memory() -> str:
    """All the notes joined into one text for the brain to read."""
    make_private_folders()
    parts = []
    for note in sorted(MEMORY.rglob("*.md")):
        parts.append(f"----- note: {note.relative_to(MEMORY)} -----\n{note.read_text().strip()}\n")
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
