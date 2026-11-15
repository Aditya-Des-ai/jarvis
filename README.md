# Jarvis

A personal assistant that lives on my laptop, knows what I'm working on across
my whole life, and **speaks first** when something is worth saying.

## What it does, in plain words

1. **It watches.** Small scripts note which app I'm using, which sites I visit,
   when I code, and what I commit.
2. **It remembers.** It keeps simple text notes about my goals, my habits and
   the decisions I've made (and why).
3. **It thinks.** Every morning it compares what I actually did with what I said
   I wanted to do.
4. **It talks.** If something stands out, it sends me a message, for example:
   *"You haven't coded in two days. Everything okay?"* I can reply, and it
   remembers the answer.

It covers several areas of life at once (for example work, study, health, sleep), so it can notice links between them and help me think through
big decisions.

## How the pieces fit

```
watchers  ->  digest  ->  brain  ->  chat
(record)     (shorten)   (think)    (talk to me)
                 |          |
                 +--> private/ <--+
                    (my data and memory)
```

## Folders

| Folder      | What it is for                                                  |
|-------------|-----------------------------------------------------------------|
| `watchers/` | Scripts that record what I'm doing on the laptop                |
| `digest/`   | Turns a day of raw records into a short, cleaned-up summary     |
| `brain/`    | The AI part: reads the summary and my memory, decides what to say |
| `chat/`     | The window where Jarvis and I talk                              |
| `schedule/` | Timers that run things in the morning and at night              |
| `safety/`   | Checks that stop my personal data from being uploaded           |
| `private/`  | **My personal data. Never uploaded.** See below.                |

## Privacy rules

- Everything Jarvis records stays in `private/` on this laptop.
- `private/` is never uploaded to GitHub. Two things enforce this: the
  `.gitignore` file, and a check in `safety/` that refuses any upload
  containing it.
- Raw records (exact window titles, exact web addresses) never leave the
  laptop. Only a shortened daily summary is shown to the AI.
- The brain is replaceable: it can be a cloud AI (smarter) or a local AI
  (fully offline) by changing one setting.

## Status

| Piece                         | State       |
|-------------------------------|-------------|
| Project layout and safety     | Done        |
| Watchers                      | Not started |
| Digest                        | Not started |
| Memory and first interview    | Not started |
| Brain and morning check-in    | Not started |
| Chat window                   | Not started |
| Voice notes                   | Not started |
| Phone messages (Telegram)     | Later       |

## Setting up on a new computer

After downloading this project, turn on the safety check once:

```
git config core.hooksPath safety
```
