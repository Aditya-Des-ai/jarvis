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
| `chat/`     | The window where Jarvis and I talk, including voice notes       |
| `schedule/` | Turns Jarvis on and off, and runs the daily check-in            |
| `safety/`   | Checks that stop my personal data from being uploaded           |
| `shared/`   | Small helpers used by all the other folders                     |
| `private/`  | **My personal data. Never uploaded.** See below.                |

`settings.toml` holds every setting, each explained in one line.

## Using it

Turn it on (once; it then starts by itself at every login):

```
bash schedule/turn_on.sh
```

Then open **http://localhost:8765**, or search "Jarvis" in the apps menu.
The first time, Jarvis interviews me about my goals in each area of life.

| I want to...                         | Do this                                              |
|--------------------------------------|------------------------------------------------------|
| Talk to Jarvis                       | Type in the chat window, or press **Voice**          |
| See if everything is running         | `bash schedule/is_it_running.sh`                     |
| Turn everything off                  | `bash schedule/turn_off.sh`                          |
| See what the brain is told about a day | `python3 -m digest.make_digest 2026-11-15`         |
| Run the morning check-in right now   | `python3 -m brain.morning_checkin --again`           |
| Read what Jarvis knows about me      | Open the notes in `private/memory/`                  |
| Give Jarvis more background          | Paste it into the chat                               |

## What is in `private/`

| Folder              | What it holds                                               |
|---------------------|-------------------------------------------------------------|
| `private/records/`  | Raw window notes and the cleaned daily summaries            |
| `private/memory/`   | Jarvis's notes about me: goals, decisions, corrections      |
| `private/chat/`     | Our conversation                                            |
| `private/context/`  | Background material I dropped in for Jarvis to read         |

These are plain text files. I can read, edit or delete any of them.

## Privacy rules

- Everything Jarvis records stays in `private/` on this laptop.
- `private/` is never uploaded to GitHub. Two things enforce this: the
  `.gitignore` file, and a check in `safety/` that refuses any upload
  containing it.
- Raw records (exact window titles, exact web addresses) never leave the
  laptop. The brain is shown only a shortened daily summary.
- In that summary each kind of activity is marked **full** (titles shown),
  **totals** (only time spent) or **hidden**. Work is full; personal things
  are totals or hidden. The rules are in `digest/categories.toml`.
- With the cloud brain, the summary, my memory notes and our conversation
  are sent to the AI company to get an answer. With the local brain nothing
  leaves the laptop, but the advice is weaker. One line in `settings.toml`
  switches between them.
- The brain is given no tools: it cannot browse, run commands or read
  files. It can only read the text handed to it and write text back.
- The chat window can only be reached from this laptop.
- Voice notes are turned into text on this laptop.

## Status

| Piece                             | State   |
|-----------------------------------|---------|
| Project layout and safety         | Done    |
| Watchers                          | Done    |
| Digest                            | Done    |
| Memory and first interview        | Done    |
| Brain and morning check-in        | Done    |
| Chat window                       | Done    |
| Voice notes                       | Done    |
| Evening wrap-up and weekly review | Later   |
| Local model for sorting activity  | Later   |
| Sleep and fitness from a wearable | Later   |
| Phone messages (Telegram)         | Later   |

## Setting up on a new computer

Needs Linux with the GNOME desktop (X11), Python 3.11 or newer, the
`claude` command, and `uv` and `ffmpeg` for voice notes.

```
git config core.hooksPath safety      # turn on the upload safety check
python3 -m brain.build_first_memory   # draft the first memory notes from my files
bash schedule/turn_on.sh              # start everything
```
