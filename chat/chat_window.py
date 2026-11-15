"""The chat window: a small web page on this laptop where Jarvis and I talk.

Open it at http://localhost:8765 (the number comes from settings.toml).

Safety:
- It only listens on this laptop, never on the network.
- Every request must carry a secret token that only the page itself knows,
  so another website open in my browser cannot read or send messages.

Run it:  python3 -m chat.chat_window
"""

import json
import secrets
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from brain.ask_brain import BrainProblem
from brain.talk import reply_to_me, say_hello
from chat.history import add_message, all_messages
from shared.settings import CHAT, PROJECT, load_settings, make_private_folders

PAGE = Path(__file__).parent / "page.html"
BIGGEST_REQUEST = 25 * 1024 * 1024   # a few minutes of voice

one_reply_at_a_time = threading.Lock()
replies_in_progress = 0


def secret_token() -> str:
    """Made once and kept in private/chat/token."""
    file = CHAT / "token"
    if not file.exists():
        file.write_text(secrets.token_urlsafe(32))
        file.chmod(0o600)
    return file.read_text().strip()


def let_jarvis_speak(first_hello: bool = False) -> None:
    """Ask the brain for Jarvis's next message, in the background."""
    global replies_in_progress
    replies_in_progress += 1
    try:
        with one_reply_at_a_time:
            messages = all_messages()
            if first_hello and not messages:
                say_hello()
            elif messages and messages[-1]["who"] == "me":   # not answered yet
                reply_to_me()
    except BrainProblem as problem:
        add_message("problem", f"I could not think just now. {problem}")
    finally:
        replies_in_progress -= 1


def voice_to_text(sound: bytes) -> str:
    """Turn a voice note into text, on this laptop."""
    with tempfile.NamedTemporaryFile(suffix=".webm") as file:
        file.write(sound)
        file.flush()
        done = subprocess.run(
            ["uv", "run", "--quiet", "--with", "faster-whisper", "python", "chat/voice_to_text.py", file.name],
            capture_output=True, text=True, timeout=600, cwd=PROJECT,
        )
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "unknown problem")
    return done.stdout.strip()


class ChatRequests(BaseHTTPRequestHandler):
    token = ""
    allowed_hosts: set[str] = set()

    def log_message(self, *_):   # keep the terminal quiet
        pass

    def answer(self, code: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def answer_json(self, data: dict, code: int = 200) -> None:
        self.answer(code, json.dumps(data, ensure_ascii=False).encode())

    def came_from_my_page(self) -> bool:
        return (
            self.headers.get("Host") in self.allowed_hosts
            and secrets.compare_digest(self.headers.get("X-Jarvis-Token", ""), self.token)
        )

    def do_GET(self):
        if self.headers.get("Host") not in self.allowed_hosts:
            return self.answer_json({"problem": "not allowed"}, 403)
        if self.path == "/":
            page = PAGE.read_text().replace("__TOKEN__", self.token)
            return self.answer(200, page.encode(), "text/html; charset=utf-8")
        if self.path == "/messages" and self.came_from_my_page():
            return self.answer_json({"messages": all_messages(), "thinking": replies_in_progress > 0})
        self.answer_json({"problem": "not found"}, 404)

    def do_POST(self):
        if not self.came_from_my_page():
            return self.answer_json({"problem": "not allowed"}, 403)
        size = int(self.headers.get("Content-Length") or 0)
        if size > BIGGEST_REQUEST:
            return self.answer_json({"problem": "too big"}, 413)
        body = self.rfile.read(size)

        if self.path == "/send":
            try:
                text = str(json.loads(body).get("text", "")).strip()
            except (json.JSONDecodeError, AttributeError):
                text = ""
            if not text:
                return self.answer_json({"problem": "empty message"}, 400)
            add_message("me", text)
            threading.Thread(target=let_jarvis_speak, daemon=True).start()
            return self.answer_json({"ok": True})

        if self.path == "/voice":
            try:
                return self.answer_json({"text": voice_to_text(body)})
            except (RuntimeError, subprocess.SubprocessError, OSError) as problem:
                return self.answer_json({"problem": f"Could not turn the voice note into text: {problem}"}, 500)

        self.answer_json({"problem": "not found"}, 404)


def main() -> None:
    make_private_folders()
    port = load_settings()["chat_port"]
    ChatRequests.token = secret_token()
    ChatRequests.allowed_hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}

    if not all_messages():
        threading.Thread(target=let_jarvis_speak, kwargs={"first_hello": True}, daemon=True).start()

    print(f"Jarvis chat is at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), ChatRequests).serve_forever()


if __name__ == "__main__":
    main()
