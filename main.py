"""
SuperLog - RBT Supervision Hour Tracker
=========================================
A command-line tool for Registered Behavior Technicians to track compliance
with BACB supervision requirements:
  - At least 5% of monthly direct service hours must be supervised
  - At least one supervision contact per month must be individual (not group)
  - At least one supervision contact per month must include direct observation

Author: Gabby
"""

# --- Standard library imports (tools that come built into Python) ---
import enum          # lets us define "enums": a fixed set of named, labeled choices
import datetime as dt  # for working with dates and times; "as dt" gives it a shorter nickname
import json          # for reading/writing data as text files in the JSON format


# =============================================================================
# ENUMS - fixed, named choices for supervision session attributes
# =============================================================================
# An enum is a way to give plain numbers human-readable names. Instead of
# remembering "1 means in-person," we can just write ObservationType.IN_PERSON.
# The number after the "=" is the value stored/saved for that choice.
#
# Why bother with an enum instead of just using 1 and 0 everywhere? Two reasons:
#   1. Readability - "ObservationType.IN_PERSON" tells you what it means at a
#      glance; a bare "1" doesn't.
#   2. Safety - Python will refuse to create ObservationType(5), so a typo like
#      that fails loudly instead of silently storing garbage data.

class ObservationType(enum.Enum):
    IN_PERSON = 1   # supervision happened face-to-face
    REMOTE = 0      # supervision happened over video/phone


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1  # one-on-one supervision (only this RBT)
    GROUP = 0       # group supervision (multiple RBTs at once)


# =============================================================================
# CLASSES - data models
# =============================================================================
# A "class" is a blueprint for creating objects that bundle related data
# together. Each object made from the blueprint holds its own values.

class WorkSession:
    """Represents one shift of direct client service work."""

    # __init__ is the "constructor": it runs automatically whenever we create a
    # new WorkSession, and "self" refers to the specific object being built.
    def __init__(self, start_time, end_time):
        # Guard against bad data: a shift can't end before (or when) it starts.
        # Raising an error here stops an invalid session from ever being created,
        # and any code that tries to build a bad WorkSession will get a
        # ValueError it can catch (see log_work_session below).
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        # Store the two values on the object so we can read them back later.
        self.start_time = start_time
        self.end_time = end_time


class SupervisionSession:
    """Represents one BCBA/RBT supervision contact."""

    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        # Same safety check as above: start must come before end.
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        self.start_time = start_time                       # when supervision began
        self.end_time = end_time                           # when supervision ended
        self.format = format                               # ObservationType (in-person/remote)
        self.session_type = session_type                   # SupervisionType (individual/group)
        self.is_direct_observation = is_direct_observation  # True/False: did they observe live work?


# =============================================================================
# DEFAULT SAMPLE DATA - used only on a brand-new install with no saved files
# =============================================================================
# These pre-filled lists give a first-time user something to look at so the
# app isn't empty. They're only used if no saved JSON files are found.

DEFAULT_WORK_SESSIONS = [
    # Each line creates one 3-hour work shift (9:30am to 12:30pm) on a given day.
    WorkSession(dt.datetime(2026, 7, 6, 9, 30), dt.datetime(2026, 7, 6, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 7, 9, 30), dt.datetime(2026, 7, 7, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 8, 9, 30), dt.datetime(2026, 7, 8, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 9, 9, 30), dt.datetime(2026, 7, 9, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 10, 9, 30), dt.datetime(2026, 7, 10, 12, 30)),
]

DEFAULT_SUPERVISION_SESSIONS = [
    # Each of these is a sample supervision contact. The last two arguments set
    # the individual/group type and whether it was a direct observation.
    SupervisionSession(dt.datetime(2026, 7, 6, 9, 30), dt.datetime(2026, 7, 6, 12, 30),
                        ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True),
    SupervisionSession(dt.datetime(2026, 7, 7, 9, 30), dt.datetime(2026, 7, 7, 12, 30),
                        ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True),
    SupervisionSession(dt.datetime(2026, 7, 8, 9, 30), dt.datetime(2026, 7, 8, 12, 30),
                        ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True),
    SupervisionSession(dt.datetime(2026, 7, 9, 9, 30), dt.datetime(2026, 7, 9, 12, 30),
                        ObservationType.IN_PERSON, SupervisionType.GROUP, False),
    SupervisionSession(dt.datetime(2026, 7, 10, 9, 30), dt.datetime(2026, 7, 10, 12, 30),
                        ObservationType.IN_PERSON, SupervisionType.GROUP, False),
]

# These two lists hold the app's live, in-memory data. load_sessions() replaces
# their contents at startup; every menu action after that modifies them directly.
# ("In-memory" just means: these values live in RAM while the program runs and
# disappear when it closes - which is exactly why save_sessions() exists, to
# copy them out to a file before that happens.)
sessions = []              # will hold WorkSession objects
supervision_sessions = []  # will hold SupervisionSession objects


# =============================================================================
# CORE COMPLIANCE LOGIC
# =============================================================================

def total_hours(session_list):
    """Sums hours across any list of sessions (works on both session types,
    since it only ever touches start_time/end_time)."""
    total = 0
    # Walk through every session in the list one at a time.
    for session in session_list:
        # Subtracting two datetimes gives a "timedelta" (a span of time).
        gap = session.end_time - session.start_time
        # Convert that span from seconds into hours (3600 seconds = 1 hour)
        # and add it to the running total.
        total = total + (gap.total_seconds() / 3600)
    return total  # hand the final number back to whoever called this


def sessions_in_month(session_list, year, month):
    """Returns only the sessions that fall within a given calendar month."""
    # This is a "list comprehension": a compact way to build a new list by
    # keeping only the sessions whose start date matches the requested year+month.
    # It's the same idea as this longer loop, just written on one line:
    #   result = []
    #   for session in session_list:
    #       if session.start_time.year == year and session.start_time.month == month:
    #           result.append(session)
    #   return result
    return [session for session in session_list
            if session.start_time.year == year and session.start_time.month == month]


def is_compliant(work_sessions, supervision_sessions, year, month):
    """BACB Rule: at least 5% of that month's worked hours were supervised."""
    # Narrow both lists down to just the month we care about.
    filtered_work = sessions_in_month(work_sessions, year, month)
    filtered_supervision = sessions_in_month(supervision_sessions, year, month)
    # 5% of the total worked hours is the minimum supervision we need.
    required_hours = total_hours(filtered_work) * .05
    # Return True if actual supervision hours meet or beat that minimum.
    return total_hours(filtered_supervision) >= required_hours


def has_individual_session(supervision_sessions):
    """BACB Rule: at least one supervision contact was individual, not group."""
    found = False  # assume none until we find one
    for session in supervision_sessions:
        if session.session_type == SupervisionType.INDIVIDUAL:
            found = True  # found at least one individual session
    return found
    # Note: this keeps looping even after it finds a match, since there's no
    # "break" here. It still gives the right answer, just does a bit of
    # unnecessary extra checking on a long list - not a bug, just something
    # you could tighten up later with an early "return True".


def has_direct_observation(supervision_sessions):
    """BACB Rule: at least one supervision contact included direct observation."""
    found = False  # assume none until we find one
    for session in supervision_sessions:
        if session.is_direct_observation:
            found = True  # found at least one direct-observation session
    return found


def generate_compliance_report(work_sessions, supervision_sessions, year, month):
    """Bundles all three BACB compliance checks for a given month into one result."""
    # Pre-filter the supervision list once so the individual/observation checks
    # only look at this month's contacts.
    month_supervision = sessions_in_month(supervision_sessions, year, month)
    # Return a dictionary (a set of labeled True/False answers) with all results.
    return {
        'is_compliant': is_compliant(work_sessions, supervision_sessions, year, month),
        'has_individual': has_individual_session(month_supervision),
        'has_direct_observation': has_direct_observation(month_supervision)
    }


# =============================================================================
# PERSISTENCE - converting objects <-> plain dictionaries for JSON storage
# =============================================================================
# JSON files can only hold simple values (text, numbers, true/false, lists,
# dictionaries) - not our custom objects or datetime/enum types. So we convert
# objects "to" dictionaries when saving, and back "from" dictionaries when loading.

def work_session_to_dict(session):
    # Turn one WorkSession object into a plain dictionary.
    # .isoformat() turns a datetime into a standard text string like "2026-07-06T09:30:00".
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat()
    }


def dict_to_work_session(data):
    # Rebuild a WorkSession object from a saved dictionary.
    # fromisoformat() is the reverse of isoformat(): text string -> datetime.
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    return WorkSession(start_time, end_time)


def supervision_session_to_dict(session):
    # Turn one SupervisionSession into a dictionary. Enums are saved as their
    # underlying number (.value) so they fit in a JSON file.
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat(),
        'format': session.format.value,
        'session_type': session.session_type.value,
        'is_direct_observation': session.is_direct_observation
    }


def dict_to_supervision_session(data):
    # Rebuild a SupervisionSession from a saved dictionary.
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    # Passing the saved number back into the enum turns it into the named choice.
    format = ObservationType(data['format'])
    session_type = SupervisionType(data['session_type'])
    is_direct_observation = data['is_direct_observation']
    return SupervisionSession(start_time, end_time, format, session_type, is_direct_observation)


def load_sessions():
    """Loads sessions from JSON files at startup. Falls back to sample data
    on a fresh install where no save files exist yet."""
    # "global" tells Python we want to change the module-level lists defined
    # above, not create new local variables that disappear when this function
    # ends. Without this line, "sessions = ..." inside the function would just
    # create a throwaway local copy and the real, app-wide list would stay empty.
    global sessions, supervision_sessions

    # "try" attempts something that might fail; "except" catches a specific failure.
    try:
        # Open the file for reading ('r'). The "with" block auto-closes it after,
        # even if something goes wrong while reading - you never have to
        # remember to close the file yourself.
        with open('work_sessions.json', 'r') as file:
            work_data = json.load(file)  # read the JSON text into a list of dicts
            # Convert every saved dictionary back into a WorkSession object.
            sessions = [dict_to_work_session(entry) for entry in work_data]
    except FileNotFoundError:
        # The file doesn't exist yet (first run) - use the sample data instead.
        print("No saved work sessions found. Starting with sample data.")
        sessions = list(DEFAULT_WORK_SESSIONS)  # list(...) makes a fresh copy

    # Same pattern again for the supervision sessions.
    try:
        with open('supervision_sessions.json', 'r') as file:
            supervision_data = json.load(file)
            supervision_sessions = [dict_to_supervision_session(entry) for entry in supervision_data]
    except FileNotFoundError:
        print("No saved supervision sessions found. Starting with sample data.")
        supervision_sessions = list(DEFAULT_SUPERVISION_SESSIONS)


def save_sessions():
    """Saves the current in-memory sessions to their JSON files."""
    # Convert every object into a dictionary the JSON library can write out.
    work_dicts = [work_session_to_dict(s) for s in sessions]
    # Open the file for writing ('w'), which overwrites the old contents.
    with open('work_sessions.json', 'w') as file:
        # indent=4 makes the saved file nicely spaced and human-readable.
        json.dump(work_dicts, file, indent=4)

    supervision_dicts = [supervision_session_to_dict(s) for s in supervision_sessions]
    with open('supervision_sessions.json', 'w') as file:
        json.dump(supervision_dicts, file, indent=4)


# =============================================================================
# MENU / USER INTERACTION
# =============================================================================

def ask_for_datetime(prompt):
    """Keep asking until the user types a date we can parse. Returns a datetime."""
    # "while True" here means "loop forever until something inside explicitly
    # stops it." The only way out of this loop is the "return" below, which
    # only runs once fromisoformat() succeeds without raising an error.
    while True:
        try:
            # Try to parse whatever the user typed into a real datetime object.
            # If it's not in a format Python understands, this line raises a
            # ValueError, control jumps straight to "except", and we never
            # reach "return" - so the loop goes around again and re-prompts.
            return dt.datetime.fromisoformat(input(prompt))
        except ValueError:
            print("Please enter a valid date and time")

def log_work_session():
    print("Format: YYYY-MM-DD HH:MM")

    # This loop handles TWO different ways things can go wrong:
    #   1. ask_for_datetime() already retries internally until it gets a
    #      parseable date, so by the time we get start_time/end_time back,
    #      the *format* is valid.
    #   2. But WorkSession(...) can still raise a ValueError even with two
    #      well-formatted dates, if end_time isn't after start_time. That's
    #      the case this outer try/except is here to catch - if it happens,
    #      we print a message and loop back to ask for BOTH times again,
    #      rather than crashing the program.
    while True:
        try:
            start_time = ask_for_datetime("Start time: ")
            end_time   = ask_for_datetime("End time: ")
            session = WorkSession(start_time, end_time)   # raises ValueError if end <= start
            break
        except ValueError:
            print("Enter a valid time")

    sessions.append(session)
    save_sessions()
    print(f"Work session logged: {start_time} to {end_time}")


def log_supervision_session():
    print("Format: YYYY-MM-DD HH:MM")
    start_time = dt.datetime.fromisoformat(input("Start time: "))
    end_time = dt.datetime.fromisoformat(input("End time: "))

    # Ask for the format as a number, then turn that number into the enum.
    format_choice = int(input("Format (1=IN_PERSON, 0=REMOTE): "))
    format_enum = ObservationType(format_choice)

    # Same idea for individual vs. group.
    type_choice = int(input("Session type (1=INDIVIDUAL, 0=GROUP): "))
    session_type_enum = SupervisionType(type_choice)

    # Read a yes/no answer. .strip() removes stray spaces, .lower() ignores case,
    # and the "== 'yes'" turns the whole thing into a True/False value.
    direct_obs = input("Direct observation? (yes/no): ").strip().lower() == "yes"

    # Build and store the new supervision session, then save.
    supervision_sessions.append(
        SupervisionSession(start_time, end_time, format_enum, session_type_enum, direct_obs)
    )
    save_sessions()
    print("Supervision session logged!")
    # NOTE: unlike log_work_session(), none of the four inputs above are
    # wrapped in try/except yet. A bad date, a non-number typed for
    # format/type, or a number outside 0/1 will currently crash the program.
    # That's item #1 on the feature list at the bottom of this file.


def view_compliance():
    # Ask which month/year the user wants a report for.
    year = int(input("Enter year (e.g., 2026): "))
    month = int(input("Enter month (1-12): "))

    # Run all three compliance checks and get back the result's dictionary.
    report = generate_compliance_report(sessions, supervision_sessions, year, month)

    # Print each result. \n adds a blank line above the header for spacing.
    print(f"\n=== Compliance Report for {month}/{year} ===")
    print(f"Is Compliant (5% rule):    {report['is_compliant']}")
    print(f"Has Individual Session:    {report['has_individual']}")
    print(f"Has Direct Observation:    {report['has_direct_observation']}")


def main_menu():
    load_sessions()  # pull in saved data (or sample data) before showing the menu

    # "while True" loops forever until we explicitly "break" out (option 4).
    while True:
        # Print the menu options every time we loop back around.
        print("\n=== SUPERLOG Menu ===")
        print("1) Log a work session")
        print("2) Log a supervision session")
        print("3) View compliance report")
        print("4) Exit")

        choice = input("Enter your choice (1-4): ")

        # Route the user's typed choice to the matching function.
        if choice == "1":
            log_work_session()
        elif choice == "2":
            log_supervision_session()
        elif choice == "3":
            view_compliance()
        elif choice == "4":
            print("Goodbye!")
            break  # leave the while loop, which ends the program
        else:
            # Anything other than 1-4 lands here and re-shows the menu.
            print("Invalid choice. Try again.")


# This special check means "only run main_menu() if this file was launched
# directly" (as opposed to being imported by another file). It's the program's
# starting point.
if __name__ == "__main__":
    main_menu()


# =============================================================================
# FEATURES STILL TO BE IMPLEMENTED
# =============================================================================
# Roughly ordered by what's most worth doing next.
#
# --- Correctness / stability ---
# 1. Input validation in log_supervision_session():
#    - Wrap the date parsing, and the format/session-type int() + enum
#      conversions, in try/except so a typo doesn't crash the whole app
#      (log_work_session already does this for dates via ask_for_datetime;
#      this function still needs the same treatment).
# 2. Corrupt-file handling:
#    - load_sessions() only catches "file missing." A file that exists but
#      contains broken/malformed JSON (e.g., from a crash mid-save) will still
#      crash the app on startup. Catch json.JSONDecodeError too.
# 3. Overlap detection:
#    - Warn (or block) when a newly logged session overlaps an existing one
#      for the same day/time range.
#
# --- Missing functionality ---
# 4. Edit and delete sessions:
#    - Let the user list existing sessions (with an index number) and remove
#      or correct one, then re-save.
# 5. View / list logged sessions:
#    - A menu option to print all work and supervision sessions for a given
#      month, not just the pass/fail summary.
# 6. Richer compliance report:
#    - Show the actual numbers (worked hours, supervised hours, % achieved),
#      not just True/False.
#    - Show exactly how many more supervision hours are needed to reach 5%.
# 7. Multiple months / history view:
#    - Summaries across a whole year, or a running "compliant streak" across
#      months.
# 8. Export:
#    - Export a monthly report to CSV or a printable text file for RBT
#      records.
#
# --- Code cleanup (no behavior change, just clarity/safety) ---
# 9. "format" parameter naming:
#    - "format" shadows Python's built-in format() function; consider
#      renaming it to observation_format.