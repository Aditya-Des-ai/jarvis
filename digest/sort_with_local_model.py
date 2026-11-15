"""Uses the small AI model on this laptop to sort apps and sites no rule recognises.

The rules in categories.toml cover the common cases. Whatever is left over
("other") is shown to a local model, which picks the closest group. Nothing
leaves the laptop: the model runs here, through Ollama.

Each answer is remembered in private/records/sorted_by_local_model.json, so
every app or site is only asked about once. To correct a wrong answer, add a
proper rule to private/my_categories.toml; rules always win.

Privacy: things sorted this way only add to a group's time total. Their
titles are never passed on to the brain, in case the local model got it wrong.

Try it:  python3 -m digest.sort_with_local_model news.ycombinator.com "Hacker News"
"""

import json
import sys
import urllib.request

from shared.settings import RECORDS, load_settings, make_private_folders

REMEMBERED = RECORDS / "sorted_by_local_model.json"
LOCAL_MODEL_ADDRESS = "http://localhost:11434/api/chat"


def describe(groups: dict) -> str:
    """One line per group with a few examples, so the model knows what each means."""
    lines = []
    for name, rules in groups.items():
        examples = (rules.get("sites", []) + rules.get("apps", []))[:5]
        lines.append(f"- {name}" + (f" (such as {', '.join(examples)})" if examples else ""))
    lines.append("- other (when none of the above fits)")
    return "\n".join(lines)


def ask_local_model(name: str, example_title: str, groups: dict, model: str) -> str | None:
    choices = [*groups, "other"]
    request = urllib.request.Request(
        LOCAL_MODEL_ADDRESS,
        data=json.dumps({
            "model": model,
            "stream": False,
            "think": False,
            "keep_alive": "1m",       # free the graphics card soon after
            "options": {"temperature": 0},
            # The model must answer with exactly one of the group names.
            "format": {
                "type": "object",
                "properties": {"group": {"type": "string", "enum": choices}},
                "required": ["group"],
            },
            "messages": [
                {"role": "system", "content":
                    "You sort computer activity into groups. You are given the name of a website or "
                    "program and one example window title. Pick the group it most likely belongs to. "
                    "If you are not sure, pick other.\n\nGroups:\n" + describe(groups)},
                {"role": "user", "content": f"Name: {name}\nExample window title: {example_title[:120]}"},
            ],
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            group = json.loads(json.loads(response.read())["message"]["content"]).get("group")
    except (OSError, KeyError, ValueError):
        return None    # the local model is not running; leave it unsorted
    return group if group in choices else None


def sort_unknown(items: dict[str, str], groups: dict) -> dict[str, str]:
    """Group for each unknown name. `items` maps a name to one example title."""
    make_private_folders()
    remembered = json.loads(REMEMBERED.read_text()) if REMEMBERED.exists() else {}
    model = load_settings()["local_model"]

    for name, example_title in items.items():
        if name in remembered:
            continue
        group = ask_local_model(name, example_title, groups, model)
        if group is None:
            break          # not reachable right now; try again another day
        remembered[name] = group

    REMEMBERED.write_text(json.dumps(remembered, indent=1, ensure_ascii=False))
    return {name: remembered[name] for name in items if name in remembered}


if __name__ == "__main__":
    from digest.make_digest import load_categories
    name = sys.argv[1] if len(sys.argv) > 1 else "news.ycombinator.com"
    title = sys.argv[2] if len(sys.argv) > 2 else ""
    answer = ask_local_model(name, title, load_categories(), load_settings()["local_model"])
    print(answer or "The local model is not running.")
