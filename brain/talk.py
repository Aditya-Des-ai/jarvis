"""Jarvis's side of the conversation.

Gathers what the brain needs to read (memory notes, recent activity
summaries, the conversation so far), asks it for the next message, and
saves anything it wanted to remember.

Try it:  python3 -m brain.talk "I skipped the gym today"
"""

import sys
from datetime import datetime
from pathlib import Path

from brain.ask_brain import think
from brain.memory import interview_finished, read_memory, save_what_to_remember
from chat.history import add_message, all_messages, as_text
from digest.make_digest import recent_digests
from shared.settings import load_settings

WHO_JARVIS_IS = (Path(__file__).parent / "who_jarvis_is.md").read_text()
MESSAGES_TO_SHOW_BRAIN = 40

FIRST_INTERVIEW = """
## Right now: the first interview

You have not finished getting to know them. Your notes were drafted from their old files, so parts are guesses and parts are missing. Before anything else, fill the gaps, one area of life at a time:

- what they are trying to achieve there, concretely, and by when
- where things stand today
- what a good week looks like, so you can recognise a bad one
- what usually gets in the way
- how direct they want you to be about this area

Also learn their daily rhythm (when they want to sleep and wake, when they work best) and what kind of nudges would annoy them.

Start from what the notes already say and ask them to confirm or correct it, rather than asking from scratch. One or two questions per message. Save what you learn to the area notes as you go. If they want to talk about something else, do that and come back to the interview later.

When every area is covered, give a five-line summary of what you understood, and put <interview_finished/> in that message.
"""


def what_the_brain_reads() -> str:
    settings = load_settings()
    return "\n\n".join([
        f"NOW: {datetime.now():%A %d %B %Y, %H:%M}",
        "===== YOUR MEMORY NOTES =====\n" + read_memory(),
        "===== THEIR RECENT LAPTOP ACTIVITY (cleaned summaries, oldest first) =====\n"
        + recent_digests(settings["days_of_history_for_brain"]),
        "===== THE CONVERSATION SO FAR (latest last) =====\n"
        + as_text(all_messages()[-MESSAGES_TO_SHOW_BRAIN:]),
    ])


def instructions() -> str:
    return WHO_JARVIS_IS if interview_finished() else WHO_JARVIS_IS + FIRST_INTERVIEW


def next_message(task: str, job: str = "chat") -> str:
    """Ask the brain for Jarvis's next message, and store what it wants to remember."""
    reply = think(instructions(), what_the_brain_reads() + "\n\n===== YOUR TASK =====\n" + task, job)
    return save_what_to_remember(reply)


def reply_to_me() -> str:
    """Answer the latest message I sent (already saved in the history)."""
    reply = next_message("Write your next message to them. Write only the message itself.")
    add_message("jarvis", reply)
    return reply


def say_hello() -> str:
    """The very first message, before anything has been said."""
    reply = next_message(
        "This is your first message to them ever. In a few sentences: say who you are, say what you "
        "already gathered about them from their notes (two or three specifics, so they can see you read them), "
        "and begin the interview with your first question. Write only the message itself."
    )
    add_message("jarvis", reply)
    return reply


if __name__ == "__main__":
    add_message("me", " ".join(sys.argv[1:]) or "Hello")
    print(reply_to_me())
