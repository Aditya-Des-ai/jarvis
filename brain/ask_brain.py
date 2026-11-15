"""The one place where Jarvis asks an AI model to think.

Everything else in the project calls think(). Which model answers is decided
by the "brain" line in settings.toml, so switching between the cloud model
and a fully offline one is a one-line change.

Safety: the model is given no tools at all. It cannot browse the web, run
commands or read files. It can only read the text handed to it and write
text back. So even if a web page title tried to trick it, it has no way to
send my data anywhere.

Try it:  python3 -m brain.ask_brain "Say hello in five words"
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime

from shared.settings import RECORDS, load_settings, make_private_folders

USAGE_RECORD = RECORDS / "brain_usage.jsonl"


class BrainProblem(Exception):
    """The model could not be reached or gave no answer."""


def think(instructions: str, material: str, job: str = "chat") -> str:
    """Ask the brain. `instructions` say who it is; `material` is what it reads.

    job is "checkins", "chat" or "deep". It picks which Claude model is used
    and how hard it thinks (see settings.toml).
    """
    settings = load_settings()
    if settings["brain"] == "local":
        return ask_local_model(instructions, material, settings["local_model"])
    return ask_claude(
        instructions, material, settings[f"claude_model_for_{job}"], settings[f"effort_for_{job}"], job
    )


def note_usage(job: str, model: str, answer: dict) -> None:
    """Keep a local record of how much each call used, so I can see what Jarvis costs me."""
    used = answer.get("usage") or {}
    make_private_folders()
    with USAGE_RECORD.open("a") as file:
        file.write(json.dumps({
            "time": datetime.now().isoformat(timespec="seconds"),
            "job": job,
            "model": model,
            "words_in": used.get("input_tokens", 0) + used.get("cache_creation_input_tokens", 0)
            + used.get("cache_read_input_tokens", 0),
            # The part that was read from the cache, which costs a small fraction of the rest.
            "of_which_cached": used.get("cache_read_input_tokens", 0),
            "words_out": used.get("output_tokens", 0),
            "price_if_paid_per_use": round(answer.get("total_cost_usd") or 0, 4),
        }) + "\n")


# One command-line argument cannot be longer than this on Linux.
LONGEST_INSTRUCTIONS = 100_000


def ask_claude(instructions: str, material: str, model: str, effort: str, job: str = "chat") -> str:
    # The instructions are the part that stays the same from one message to the
    # next, so Claude can reuse them from its cache at a fraction of the cost.
    if len(instructions.encode()) > LONGEST_INSTRUCTIONS:
        material = instructions + "\n\n" + material
        instructions = "Follow the instructions at the start of the message."

    # Start clean: no settings from other Claude Code sessions, no saved history.
    clean = {name: value for name, value in os.environ.items() if not name.startswith("CLAUDE")}
    clean["PATH"] = os.path.expanduser("~/.local/bin") + ":" + clean.get("PATH", "/usr/bin:/bin")

    command = [
        "claude", "--print",
        "--model", model,
        "--effort", effort,
        "--system-prompt", instructions,
        "--tools", "",                  # no tools at all
        "--strict-mcp-config",          # no connectors (mail, drive and so on)
        "--disable-slash-commands",
        "--setting-sources", "",
        "--no-session-persistence",     # do not save this exchange as a Claude Code session
        "--output-format", "json",
    ]
    with tempfile.TemporaryDirectory() as empty_folder:
        try:
            done = subprocess.run(
                command, input=material, capture_output=True, text=True,
                timeout=300, cwd=empty_folder, env=clean,
            )
        except (subprocess.SubprocessError, OSError) as problem:
            raise BrainProblem(f"Could not run Claude: {problem}") from problem

    try:
        answer = json.loads(done.stdout)
    except json.JSONDecodeError as problem:
        raise BrainProblem(f"Claude gave no readable answer: {done.stderr[:300] or done.stdout[:300]}") from problem
    if answer.get("is_error") or not answer.get("result"):
        raise BrainProblem(f"Claude reported a problem: {str(answer.get('result'))[:300]}")
    note_usage(job, model, answer)
    return answer["result"].strip()


def ask_local_model(instructions: str, material: str, model: str) -> str:
    """Fully offline, through Ollama running on this laptop."""
    request = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps({
            "model": model,
            "stream": False,
            "keep_alive": "5m",
            # Room to read the notes, the summaries and the conversation.
            "options": {"num_ctx": 20000},
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": material},
            ],
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read())["message"]["content"].strip()
    except (OSError, KeyError, json.JSONDecodeError) as problem:
        raise BrainProblem(
            f"Could not reach the local model '{model}'. Is Ollama installed and running? ({problem})"
        ) from problem


if __name__ == "__main__":
    print(think("You are a helpful assistant. Answer briefly.", " ".join(sys.argv[1:]) or "Say hello."))
