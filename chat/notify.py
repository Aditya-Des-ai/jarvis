"""Shows a desktop notification when Jarvis has something to say.

The notification has an "Open chat" button that opens the chat window.

Try it:  python3 -m chat.notify "Hello from Jarvis"
"""

import subprocess
import sys

from shared.settings import load_settings

LONGEST_PREVIEW = 220


def chat_address() -> str:
    return f"http://localhost:{load_settings()['chat_port']}"


def notify(text: str) -> None:
    """Show the notification without waiting for me to click it."""
    subprocess.Popen(
        [sys.executable, "-m", "chat.notify", text],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )


def show_and_wait(text: str) -> None:
    preview = text if len(text) <= LONGEST_PREVIEW else text[:LONGEST_PREVIEW].rsplit(" ", 1)[0] + "..."
    try:
        clicked = subprocess.run(
            ["notify-send", "--app-name=Jarvis", "--icon=user-available", "--expire-time=0",
             "--action=open=Open chat", "Jarvis", preview],
            capture_output=True, text=True, timeout=3600,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return
    if clicked == "open":
        subprocess.Popen(["xdg-open", chat_address()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    show_and_wait(" ".join(sys.argv[1:]) or "Hello from Jarvis")
