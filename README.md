# SuperLog

SuperLog is a browser-based RBT supervision tracker for recording work hours, supervision contacts, and monthly compliance checks.

It is a local Python application that stores data in JSON files. It is intended for personal use and small-team testing, not internet-facing production deployment.

## Features

- Register, sign in, and sign out
- Store separate work and supervision data for each user
- Create, edit, and delete work sessions
- Create, edit, and delete supervision sessions
- Prevent overlapping sessions while allowing back-to-back sessions
- View a monthly dashboard and report
- View a yearly activity summary
- Calculate work hours, supervision hours, required supervision hours, and remaining hours
- Protect state-changing browser actions with CSRF tokens
- Use signed session cookies

## Compliance Checks

The current report evaluates three requirements for the selected month:

1. Supervision hours are at least 5% of recorded work hours.
2. At least one supervision contact is individual.
3. At least one supervision contact includes direct observation.

The overall compliance result is true only when all three checks pass. The application is a tracking aid and does not replace current guidance from the Behavior Analyst Certification Board (BACB). Verify requirements against the current official BACB rules before relying on a report for formal compliance purposes.

The 50% individual-supervision-hours rule is not currently implemented.

## Requirements

- Python 3.10 or newer is recommended.
- The application uses Python standard-library modules and does not require third-party packages.

## Run Locally

From the project directory, run:

```text
python app.py
```

Then open:

```text
http://127.0.0.1:5001
```

To use another host or port:

```text
python app.py --host 127.0.0.1 --port 5001
```

Create an account from the registration page, or use the local development account below.

## Local Test Account

```text
Username: demo
Password: Demo123!
```

This account is for local testing only. Change or remove it before sharing the application or deploying it anywhere accessible to other people.

## Run Tests

Run all discovered tests with:

```text
python -m unittest discover -s tests -v
```

The current compliance test suite covers:

- A fully compliant month
- Supervision below 5%
- Missing individual supervision
- Missing direct observation
- Back-to-back sessions
- Overlapping sessions

## Data Storage

Authentication records are stored in:

```text
users.json
```

Each user's session data is stored under a folder based on the username:

```text
data/<username>/work_sessions.json
data/<username>/supervision_sessions.json
```

Back up both `users.json` and the complete `data/` directory. Deleting `users.json` removes the account records but does not remove the session files under `data/`.

## Security Notes

- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with per-password salts.
- Session cookies are signed with `SUPERLOG_SECRET_KEY`.
- The default secret is suitable only for local development. Set a strong environment variable before any shared deployment:

```text
SUPERLOG_SECRET_KEY=replace-with-a-long-random-secret
```

- The current JSON storage still needs atomic-write and deployment hardening before the application should be exposed publicly.

## Known Limitations

- No CSV or PDF export yet.
- No audit trail for edits and deletes yet.
- No password reset or administrator account management yet.
- No backup and restore workflow yet.
- The 50% individual-supervision-hours rule is not implemented.
- JSON files are not a substitute for a production database.
- The older command-line implementation in `superlog.py` is legacy; the supported browser entry point is `app.py`.

## Roadmap

1. Add route and persistence tests, including two-user isolation.
2. Make JSON writes atomic and preserve corrupted files for recovery.
3. Add CSV export and printable monthly reports.
4. Add audit history and account-management workflows.
5. Add validated backup and restore.
6. For internet-facing deployment, migrate to a database and production web server with HTTPS, rate limiting, secret management, and structured logging.