# SuperLog

A browser-based RBT supervision tracker for logging work hours, supervision sessions, and monthly BACB compliance checks.

## Why This Exists

If you're an RBT, you already know the basics: at least 5% of your monthly direct service hours need to be supervised, you need at least one individual supervision contact per month, and at least one contact has to include direct observation. A lot of people track that in a spreadsheet, a notes app, or just keep it in their head until audit time.

I built SuperLog to solve that problem with a simple browser app, using only Python and local JSON files.

## What It Does

- Log work sessions and supervision sessions with real dates and times
- Edit or delete saved sessions in the browser
- View month and year summaries
- Calculate whether the 5% supervision requirement is met
- Check whether you have at least one individual contact and one direct observation session
- Save data to disk so it persists between runs
- Support login, registration, logout, and per-user private data storage
- Protect state-changing actions with CSRF tokens

## Authentication And Data Storage

SuperLog now supports lightweight authentication for internal testing and small-team use.

- User accounts are stored in `users.json`
- Each user gets private session data under `data/<username>/`
- Work sessions are saved in `data/<username>/work_sessions.json`
- Supervision sessions are saved in `data/<username>/supervision_sessions.json`
- Session cookies are signed, and POST actions require a CSRF token

## What It Does Not Do Yet

- It still tracks one user's data at a time per account
- It does not yet check the “50% of supervision hours must be individual” rule
- It does not yet generate PDF or CSV exports
- It does not yet keep an audit trail for edits and deletes

## Current Roadmap

Better account management. Right now login exists, but for real users I want a cleaner way to create, disable, and reset accounts without editing files by hand. That matters as soon as more than one person is using it.

Audit history for edits and deletes. When multiple people are logging sessions, I need to know who changed what and when. That protects against accidental data loss and makes the app trustworthy for compliance use.

Export and backup. Let users download their data or monthly reports as CSV or PDF, and give me an easy recovery path if something goes wrong. That is the main safety net before wider testing.