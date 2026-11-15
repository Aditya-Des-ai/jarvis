"""The morning check-in: Jarvis looks at yesterday and decides whether to speak.

Runs once a day on a timer. It compares what I actually did with my goals
and commitments. If something is worth raising, it writes a message in the
chat and shows a desktop notification. If nothing is, it stays quiet.

Run it by hand:  python3 -m brain.morning_checkin
"""

import sys
import time
from datetime import date

from brain.ask_brain import BrainProblem
from brain.talk import next_message
from chat.history import add_message, all_messages
from chat.notify import notify
from shared.settings import CHAT, make_private_folders
from watchers.notion_pages import NotionProblem, fetch_notion

NOTHING_TO_SAY = "NOTHING"

TASK = f"""It is the morning check-in. Nobody asked you anything; you are deciding whether to speak first.

Look at yesterday (and the days before it) against what your notes say they want: their goals, what a good week looks like in each area, anything in things_to_bring_up.md, and anything they said in conversation they would do. Look across areas too, for example late nights followed by short work days.

Then decide. Speak if there is something a good friend who knew all this would raise: a real drift from what they said they wanted, a streak worth acknowledging, something due, or a question whose answer you need to understand them better. Raise the one or two things that matter most, not a list.

Stay quiet if yesterday was ordinary and nothing is due. A check-in that says nothing useful every morning teaches them to ignore you. In that case reply with exactly: {NOTHING_TO_SAY}

If the first interview is not finished and the conversation has gone quiet, a short nudge to continue it counts as worth saying.

If you speak, write only the message itself: two to five sentences, with the actual numbers, ending with one question when you need an answer."""


def already_ran_today() -> bool:
    marker = CHAT / "last_checkin"
    return marker.exists() and marker.read_text().strip() == str(date.today())


def main() -> None:
    make_private_folders()
    if already_ran_today() and "--again" not in sys.argv:
        print("Already checked in today. Use --again to run it anyway.")
        return

    try:
        fetch_notion()      # does nothing unless a Notion key is set
    except NotionProblem as problem:
        print(problem)

    message = None
    for attempt in range(3):    # the laptop may have just woken up with no internet yet
        try:
            message = next_message(TASK, job="checkins")
            break
        except BrainProblem as problem:
            print(f"Try {attempt + 1} failed: {problem}")
            time.sleep(60)
    if message is None:
        return

    (CHAT / "last_checkin").write_text(str(date.today()))
    if message.strip().upper().startswith(NOTHING_TO_SAY):
        print("Nothing worth saying today.")
        return

    if not all_messages():
        print("No conversation yet; the chat window will open with Jarvis's hello instead.")
        return
    add_message("jarvis", message)
    notify(message)
    print(message)


if __name__ == "__main__":
    main()
