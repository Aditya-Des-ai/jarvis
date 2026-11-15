"""Where everything lives on disk, and how to read the settings."""

import tomllib
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# Everything personal lives under private/ and is never uploaded.
PRIVATE = PROJECT / "private"
RECORDS = PRIVATE / "records"          # raw activity, one file per day
WINDOW_RECORDS = RECORDS / "windows"
DIGESTS = RECORDS / "digests"          # cleaned daily summaries
MEMORY = PRIVATE / "memory"            # what Jarvis knows about me
CONTEXT = PRIVATE / "context"          # extra material I drop in for Jarvis to read
CHAT = PRIVATE / "chat"                # our conversation history


def load_settings() -> dict:
    """Read settings.toml, then let private/settings.toml override it."""
    settings = tomllib.loads((PROJECT / "settings.toml").read_text())
    mine = PRIVATE / "settings.toml"
    if mine.exists():
        settings.update(tomllib.loads(mine.read_text()))
    return settings


def make_private_folders() -> None:
    for folder in (WINDOW_RECORDS, DIGESTS, MEMORY, MEMORY / "areas", CONTEXT, CHAT):
        folder.mkdir(parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
