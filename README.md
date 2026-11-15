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

It covers several areas of life at once (for example work, study, health,
sleep), so it can notice links between them and help me think through big
decisions.

## How the pieces fit

```
watchers  ->  digest  ->  brain  ->  chat
(record)     (shorten)   (think)    (talk to me)
                 |          |
                 +--> private/ <--+
                    (my data and memory)
```

## Getting started

Needs Linux with the GNOME desktop (X11), Python 3.11 or newer and the
[`claude`](https://claude.com/claude-code) command. Voice notes also need
`uv` and `ffmpeg`.

```
git clone <this project> && cd jarvis
git config core.hooksPath safety      # turn on the upload safety check
python3 -m brain.build_first_memory   # draft the first memory notes from my files
bash schedule/turn_on.sh              # start everything, add the "jarvis" command
jarvis                                # open the chat
```

The first time, Jarvis interviews me about my goals in each area of life.

## The `jarvis` command

| I type            | What happens                                              |
|-------------------|-----------------------------------------------------------|
| `jarvis`          | The chat opens in its own small window                    |
| `jarvis on`       | Turns Jarvis on, and keeps it on after every login        |
| `jarvis off`      | Turns Jarvis off; nothing is recorded                     |
| `jarvis status`   | Shows whether each part is running                        |
| `jarvis today`    | Shows exactly what the brain is told about today          |
| `jarvis checkin`  | Runs the morning check-in right now                       |
| `jarvis read`     | Reads new background I put in `private/context/`          |
| `jarvis notion`   | Copies my Notion pages, then reads what is new            |
| `jarvis usage`    | Shows how much of my AI allowance Jarvis has used         |

In the chat I can type, or press **Voice** to speak. Jarvis also appears in
the apps menu, and its notifications have an "Open chat" button.

## Folders

| Folder      | What it is for                                                  |
|-------------|-----------------------------------------------------------------|
| `watchers/` | Scripts that record what I'm doing, and copy my Notion pages    |
| `digest/`   | Turns a day of raw records into a short, cleaned-up summary     |
| `brain/`    | The AI part: reads the summary and my memory, decides what to say |
| `chat/`     | The window where Jarvis and I talk, including voice notes       |
| `schedule/` | Turns Jarvis on and off, and runs the daily check-in            |
| `safety/`   | Checks that stop my personal data from being uploaded           |
| `shared/`   | Small helpers used by all the other folders                     |
| `private/`  | **My personal data. Never uploaded.** See below.                |

`settings.toml` holds every setting, each explained in one line.
`jarvis` is the short command.

## What is in `private/`

| Inside `private/`     | What it holds                                             |
|-----------------------|-----------------------------------------------------------|
| `records/`            | Raw window notes and the cleaned daily summaries          |
| `memory/`             | Jarvis's notes about me: goals, decisions, corrections    |
| `chat/`               | Our conversation                                          |
| `context/`            | Background material for Jarvis to read                    |
| `settings.toml`       | My own settings and keys                                  |
| `my_categories.toml`  | My own rules for sorting apps and websites                |
| `never_publish.txt`   | Words that must never be uploaded (my name, my email...)  |

These are plain text files. I can read, edit or delete any of them.

## Giving Jarvis background, and what happens to old material

I can drop text files into `private/context/` (summaries of old chats, notes)
and run `jarvis read`. Each file is read once and what matters is added to
the notes. Nothing already in the notes is overwritten.

People change, so every file gets an age. A line near the top sets it:

```
Period: March 2026 to April 2026
```

- **Recent** material goes into the notes for each area of my life.
- **Old** material (older than `old_after_days` in `settings.toml`), or
  material with no date, is kept as history in `memory/past.md`. Jarvis asks
  me whether it still applies before treating any of it as a current goal.

## Connecting Notion

Optional. Jarvis only sees the Notion pages I share with it.

1. In Notion, go to **Settings → Connections → Develop or manage integrations**
   and create a new *internal* integration. Give it **read content** only.
2. Copy its secret key into `private/settings.toml`:
   `notion_key = "secret_..."`
3. In Notion, open each page or tracker Jarvis may read, click **••• →
   Connections** and add the integration. Sharing a page shares its sub-pages.
4. Run `jarvis notion`.

Pages are copied into `private/context/notion/`. Pages not edited for a long
time are copied only as a short opening and treated as history. Trackers keep
only their recent rows, and what I log in them shows up in the daily summary.

## The local AI model

Optional. `bash schedule/get_local_model.sh` downloads a small model (about
4 GB) that runs on this laptop with no internet. It is used for two things:

- sorting apps and websites that no rule in `digest/categories.toml`
  recognises, so less of my day ends up as "other";
- being the whole brain, if I set `brain = "local"` in `settings.toml`. Then
  nothing at all leaves the laptop, but the advice is noticeably weaker.

## Privacy rules

- Everything Jarvis records stays in `private/` on this laptop.
- `private/` is never uploaded. Three things enforce this: the `.gitignore`
  file, a check in `safety/` that refuses any upload containing it, and a
  second check that refuses any upload containing a word from
  `private/never_publish.txt`.
- Raw records (exact window titles, exact web addresses) never leave the
  laptop. The brain is shown only a shortened daily summary.
- In that summary each kind of activity is marked **full** (titles shown),
  **totals** (only time spent) or **hidden**. Work is full; personal things
  are totals or hidden. The rules are in `digest/categories.toml`.
- With the cloud brain, the summary, my memory notes and our conversation
  are sent to the AI company to get an answer. With the local brain nothing
  leaves the laptop. One line in `settings.toml` switches between them.
- The brain is given no tools: it cannot browse, run commands or read
  files. It can only read the text handed to it and write text back.
- The chat window can only be reached from this laptop.
- Voice notes are turned into text on this laptop.

## Status

| Piece                                            | State                                   |
|--------------------------------------------------|-----------------------------------------|
| Watchers, digest, memory, brain, chat            | Working                                 |
| Voice notes                                      | Working                                 |
| Short `jarvis` command                           | Working                                 |
| Local model for sorting activity                 | Working                                 |
| Reading background, with old material kept apart | Working                                 |
| Notion                                           | Written, not yet tried on a real account |
| Evening wrap-up and weekly review                | Later                                   |
| Sleep and fitness from a wearable                | Later                                   |
| Phone messages                                   | Later                                   |

## License

MIT. Use it, change it, share it. See `LICENSE`.
