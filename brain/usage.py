"""Shows how much of my AI allowance Jarvis has used.

Every call to the cloud brain is noted in private/records/brain_usage.jsonl.
"Words" here are tokens, the unit AI models count in (roughly 3/4 of a word).
The price is what the same calls would cost if paid per use; on a
subscription nothing is charged, but it shows how heavy the use is.

Run it:  python3 -m brain.usage     (or: jarvis usage)
"""

import json
from collections import defaultdict
from datetime import date, timedelta

from brain.ask_brain import USAGE_RECORD


def main() -> None:
    if not USAGE_RECORD.exists():
        print("No use recorded yet.")
        return
    by_day: dict[str, dict] = defaultdict(lambda: {"calls": 0, "words_in": 0, "words_out": 0, "price": 0.0})
    for line in USAGE_RECORD.read_text().splitlines():
        try:
            call = json.loads(line)
        except json.JSONDecodeError:
            continue
        day = by_day[call["time"][:10]]
        day["calls"] += 1
        day["words_in"] += call["words_in"]
        day["words_out"] += call["words_out"]
        day["price"] += call["price_if_paid_per_use"]

    week_ago = str(date.today() - timedelta(days=7))
    print(f"{'day':<12}{'calls':>6}{'read':>12}{'written':>10}{'if paid per use':>18}")
    for name in sorted(by_day)[-14:]:
        day = by_day[name]
        print(f"{name:<12}{day['calls']:>6}{day['words_in']:>12,}{day['words_out']:>10,}{'$' + format(day['price'], '.2f'):>18}")
    week = sum(day["price"] for name, day in by_day.items() if name > week_ago)
    print(f"\nLast 7 days: ${week:.2f} if it had been paid per use.")


if __name__ == "__main__":
    main()
