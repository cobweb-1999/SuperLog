# SuperLog

A command-line tool for RBTs to track supervision hours and stay compliant with BACB requirements — built because I got tired of tracking mine in a Notes app.

## Why this exists

If you're an RBT, you already know: at least 5% of your monthly direct service hours need to be supervised, you need at least one individual (not group) contact per month, and at least one session has to include direct observation. There's no official app for this. Most people track it in a spreadsheet, a Notes app, or just... don't, until it's audit time and they're scrambling.

I'm an RBT and a cybersecurity student learning Python, so I built this both to actually solve the problem and to learn by building something real instead of doing tutorial exercises.

## What it does right now

- Log work sessions and supervision sessions with real dates/times
- Calculates whether you've hit the 5% supervision requirement for a given month
- Checks whether you've had at least one individual contact and one direct observation session
- Saves everything to disk, so your data is still there next time you open it

## What it doesn't do yet

- No GUI — it's a terminal menu right now
- No edit/delete for a session you logged by mistake (coming soon)
- Only tracks one person's data at a time
- Doesn't check the 50%-of-hours-must-be-individual rule yet, only the "at least one" rules

## Running it

You'll need Python 3 installed. Clone this repo, then:

```
python main.py
```

It'll walk you through a simple menu — log sessions, view your compliance report, exit. Your data saves automatically to two JSON files in the same folder.

## Status

Currently being tested by a couple of BCBAs at the ABA center where I work. Still early — expect rough edges. If something breaks or is confusing, I want to know about it.

## Built with

Python, `datetime`, `enum`, `json`. No external dependencies, no database — just plain files. Kept it simple on purpose while I was still learning.

## License

Not decided yet.
