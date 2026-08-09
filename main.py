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
import os            # for filesystem checks (os.path.exists) and file removal (os.remov

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_SESSIONS_FILE = os.path.join(BASE_DIR, 'work_sessions.json')
SUPERVISION_SESSIONS_FILE = os.path.join(BASE_DIR, 'supervision_sessions.json')


# =============================================================================
# ENUMS - fixed, named choices for supervision session attributes
# =============================================================================
class ObservationType(enum.Enum):
    IN_PERSON = 1   # supervision happened face-to-face
    REMOTE = 0      # supervision happened over video/phone


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1  # one-on-one supervision (only this RBT)
    GROUP = 0       # group supervision (multiple RBTs at once)


# =============================================================================
# CLASSES - data models
# =============================================================================
class WorkSession:
    """Represents one shift of direct client service work."""

    def __init__(self, start_time, end_time):
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        self.start_time = start_time
        self.end_time = end_time


class SupervisionSession:
    """Represents one BCBA/RBT supervision contact."""

    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        self.start_time = start_time
        self.end_time = end_time
        self.format = format
        self.session_type = session_type
        self.is_direct_observation = is_direct_observation


# =============================================================================
# DEFAULT SAMPLE DATA - used only on a brand-new install with no saved files
# =============================================================================
DEFAULT_WORK_SESSIONS = [
    WorkSession(dt.datetime(2026, 7, 6, 9, 30), dt.datetime(2026, 7, 6, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 7, 9, 30), dt.datetime(2026, 7, 7, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 8, 9, 30), dt.datetime(2026, 7, 8, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 9, 9, 30), dt.datetime(2026, 7, 9, 12, 30)),
    WorkSession(dt.datetime(2026, 7, 10, 9, 30), dt.datetime(2026, 7, 10, 12, 30)),
]

DEFAULT_SUPERVISION_SESSIONS = [
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

sessions = []              # will hold WorkSession objects
supervision_sessions = []  # will hold SupervisionSession objects


# =============================================================================
# CORE COMPLIANCE LOGIC
# =============================================================================
def total_hours(session_list):
    """Sums hours across any list of sessions."""
    total = 0
    for session in session_list:
        gap = session.end_time - session.start_time
        total = total + (gap.total_seconds() / 3600)
    return total


def sessions_in_month(session_list, year, month):
    """Returns only the sessions that fall within a given calendar month."""
    return [session for session in session_list
            if session.start_time.year == year and session.start_time.month == month]


def is_compliant(work_sessions, supervision_sessions, year, month):
    """BACB Rule: at least 5% of that month's worked hours were supervised."""
    filtered_work = sessions_in_month(work_sessions, year, month)
    filtered_supervision = sessions_in_month(supervision_sessions, year, month)
    required_hours = total_hours(filtered_work) * .05
    return total_hours(filtered_supervision) >= required_hours


def has_individual_session(supervision_sessions):
    """BACB Rule: at least one supervision contact was individual, not group."""
    found = False
    for session in supervision_sessions:
        if session.session_type == SupervisionType.INDIVIDUAL:
            found = True
    return found
    # NOTE: no early "break"/"return True" - keeps scanning after a match.
    # Correct, just not optimal. Same pattern check_overlap() now avoids.


def has_direct_observation(supervision_sessions):
    """BACB Rule: at least one supervision contact included direct observation."""
    found = False
    for session in supervision_sessions:
        if session.is_direct_observation:
            found = True
    return found

# =============================================================================
# PERSISTENCE - converting objects <-> plain dictionaries for JSON storage
# =============================================================================
def work_session_to_dict(session):
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat()
    }


def dict_to_work_session(data):
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    return WorkSession(start_time, end_time)


def supervision_session_to_dict(session):
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat(),
        'format': session.format.value,
        'session_type': session.session_type.value,
        'is_direct_observation': session.is_direct_observation
    }


def dict_to_supervision_session(data):
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    format = ObservationType(data['format'])
    session_type = SupervisionType(data['session_type'])
    is_direct_observation = data['is_direct_observation']
    return SupervisionSession(start_time, end_time, format, session_type, is_direct_observation)


def load_sessions(use_sample_data=True):
    """Loads sessions from JSON files at startup. Falls back to sample data
    on a fresh install, and also recovers from a corrupted save file by
    deleting it and using sample data instead. [DONE - both blocks below]"""
    global sessions, supervision_sessions

    try:
        with open(WORK_SESSIONS_FILE, 'r') as file:
            work_data = json.load(file)
            sessions = [dict_to_work_session(entry) for entry in work_data]
    except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
        if use_sample_data:
            print("Error decoding JSON file. Using default data.")
            sessions = list(DEFAULT_WORK_SESSIONS)
        else:
            sessions = []
        if os.path.exists(WORK_SESSIONS_FILE):
            os.remove(WORK_SESSIONS_FILE)

    try:
        with open(SUPERVISION_SESSIONS_FILE, 'r') as file:
            supervision_data = json.load(file)
            supervision_sessions = [dict_to_supervision_session(entry) for entry in supervision_data]
    except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
        if use_sample_data:
            print("Error decoding JSON file. Using default data.")
            supervision_sessions = list(DEFAULT_SUPERVISION_SESSIONS)
        else:
            supervision_sessions = []
        if os.path.exists(SUPERVISION_SESSIONS_FILE):
            os.remove(SUPERVISION_SESSIONS_FILE)


def save_sessions():
    """Saves the current in-memory sessions to their JSON files.
    NOTE: no error handling here yet (item 2b - not on your list but worth
    doing eventually: what if disk is full or the file is locked?)."""
    work_dicts = [work_session_to_dict(s) for s in sessions]
    with open(WORK_SESSIONS_FILE, 'w') as file:
        json.dump(work_dicts, file, indent=4)

    supervision_dicts = [supervision_session_to_dict(s) for s in supervision_sessions]
    with open(SUPERVISION_SESSIONS_FILE, 'w') as file:
        json.dump(supervision_dicts, file, indent=4)




# =============================================================================
# MENU / USER INTERACTION
# =============================================================================
def ask_for_datetime(prompt):
    """Keep asking until the user types a date we can parse. Returns a datetime."""
    while True:
        try:
            return dt.datetime.fromisoformat(input(prompt))
        except ValueError:
            print("Please enter a valid date and time")


def log_work_session():
    print("Format: YYYY-MM-DD HH:MM")

    while True:
        try:
            start_time = ask_for_datetime("Start time: ")
            end_time   = ask_for_datetime("End time: ")
            session = WorkSession(start_time, end_time)   # raises ValueError if end <= start
            if check_overlap(session, sessions):
                break
        except ValueError:
            print("Enter a valid time")
    sessions.append(session)
    save_sessions()
    print(f"Work session logged: {start_time} to {end_time}")


def sessions_overlap(new_session, existing_session):
    """Returns True if two individual sessions' time ranges overlap at all."""
    return (new_session.start_time <= existing_session.end_time and
            new_session.end_time >= existing_session.start_time)


def check_overlap(new_session, existing_sessions):
    """Checks new_session against every session in existing_sessions.
    Returns False (and prints a warning) as soon as any overlap is found;
    returns True if the full list was checked with no overlaps. [DONE]"""
    for existing_session in existing_sessions:
        if sessions_overlap(new_session, existing_session):
            print(f"Session overlaps with {existing_session.start_time} to {existing_session.end_time}")
            return False
    return True


def log_supervision_session():
    """Prompts for every field of a supervision session, retrying on bad
    input at each step, then builds and saves the session."""
    print("Format: YYYY-MM-DD HH:MM")

    while True:
        try:
            start_time = ask_for_datetime("Start time: ")
            end_time   = ask_for_datetime("End time: ")
            if end_time <= start_time:
                print("End time must be after start time")
                raise ValueError("End time must be after start time")
            break
        except ValueError:
            print("Enter a valid time")

    while True:
        try:
            format_choice = int(input("Format (1=IN_PERSON, 0=REMOTE): "))
            format_enum = ObservationType(format_choice)
            break
        except ValueError:
            print("Enter a valid number")

    while True:
        try:
            type_choice = int(input("Session type (1=INDIVIDUAL, 0=GROUP): "))
            session_type_enum = SupervisionType(type_choice)
            break
        except ValueError:
            print("Enter a valid number")

    while True:
        answer = input("Is this a direct observation? (yes/no): ").strip().lower()
        if answer == 'yes':
            direct_obs = True
            break
        elif answer == 'no':
            direct_obs = False
            break
        else:
            print("Enter a valid answer")

    new_session = SupervisionSession(start_time, end_time, format_enum, session_type_enum, direct_obs)

    if not check_overlap(new_session, supervision_sessions):
        print("Session not saved. Please re-enter the times.")
        return

    supervision_sessions.append(new_session)
    save_sessions()
    print("Supervision session logged!")


def view_compliance():
    year = int(input("Enter year (e.g., 2026): "))
    month = int(input("Enter month (1-12): "))

    report = generate_compliance_report(sessions, supervision_sessions, year, month)

    print(f"\n=== Compliance Report for {month}/{year} ===")
    print(f"Is Compliant (5% rule):    {report['is_compliant']}")
    print(f"Has Individual Session:    {report['has_individual']}")
    print(f"Has Direct Observation:    {report['has_direct_observation']}")

    print(f"Worked Hours: {report['work_hours']:.2f}")
    print(f"Supervised Hours: {report['supervised_hours']:.2f}")
    print(f"Required Hours: {report['required_hours']:.2f}")
    print(f"Percent of Requirement Met: {report['percent_achieved']:.2f}%")
    print(f"Hours needed to meet requirement: {report['hours_still_needed']:.2f}")



def main_menu():
    load_sessions()

    while True:
        print("\n=== SUPERLOG Menu ===")
        print("1) Log a work session")
        print("2) Log a supervision session")
        print("3) View compliance report")
        print("4) Edit/delete sessions")
        print("5) View sessions for month")
        print("6) View year summary")
        print("7) Exit")

        choice = input("Enter your choice (1-7): ")

        if choice == "1":
            log_work_session()
        elif choice == "2":
            log_supervision_session()
        elif choice == "3":
            view_compliance()
        elif choice == "4":
            session_choice = input("Work Session or Supervision Session? (1/2): ")
            if session_choice == "1":
                target_list = sessions
            elif session_choice == "2":
                target_list = supervision_sessions
            action_choice = input("Delete or Edit? (1/2): ")
            if action_choice == "1":
                delete_session(target_list)
            elif action_choice == "2":
                edit_session(target_list)
        elif choice == "5":
            view_sessions_in_month()
        elif choice == "6":
            view_year_summary()
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

def list_sessions(sessions):
    for i, session in enumerate(sessions):
        print(f"{i}: {session.start_time} to {session.end_time}")

def delete_session(session_list):
    list_sessions(session_list)

    while True:
        try:
            index = int(input("Enter the index of the session you want to delete: "))
            if 0 <= index < len(session_list):
                del session_list[index]
                save_sessions()
                print("Session deleted.")
                break
            else:
                print("Invalid index.")
        except ValueError:
            print("Please enter a valid number.")

def edit_session(session_list):
    list_sessions(session_list)

    while True:
        try:
            index = int(input("Enter the index of the session you want to edit: "))
            if 0 <= index < len(session_list):
                break
            else:
                print("Invalid index.")
        except ValueError:
            print("Please enter a valid number.")

    new_start_time = ask_for_datetime("Enter the new start time: ")
    new_end_time = ask_for_datetime("Enter the new end time: ")
    session_list[index].start_time = new_start_time
    session_list[index].end_time = new_end_time
    save_sessions()
    print("Session edited.")


def view_sessions_in_month():
    # FIX 1: Keep inputs as strings first to safely check for 'all'
    month_input = input("Enter month (1-12 or 'ALL'): ").strip().lower()
    year_input = input("Enter year (e.g., 2026): ").strip()

    if month_input == "all":
        filtered_sessions = sessions
        filtered_supervision = supervision_sessions
        display_month = "ALL"

    else:
        try:
            # FIX 5: Remove redundant casting; parse once and use directly
            month_val = int(month_input)
            year_val = int(year_input)

            if not (1 <= month_val <= 12):
                print("Invalid month. Please enter a number between 1-12.")
                return

            filtered_sessions = sessions_in_month(sessions, year_val, month_val)
            filtered_supervision = sessions_in_month(supervision_sessions, year_val, month_val)
            display_month = month_val
            display_year = year_val

        except ValueError:
            print("Invalid input. Please enter a valid month and year.")
            return

    # FIX 3: Calculate totals now that filtered lists are guaranteed to exist
    work_hours = total_hours(filtered_sessions)
    superv_hours = total_hours(filtered_supervision)

    # --- WORK SESSIONS ---
    print(f"\n=== Work Sessions for {display_month}/{display_year} ===")
    if not filtered_sessions:
        print("No work sessions recorded.")
    else:
        print(f"{'ID':<4} | {'Start Time':<20} | {'End Time':<20} | {'Duration':<12}")
        print("-" * 68)
        # FIX 4: Consistent index start (both use start=1 for user readability)
        for i, session in enumerate(filtered_sessions, start=1):
            # BONUS FIX: Parentheses fixed around the subtraction so .total_seconds() works
            duration = (session.end_time - session.start_time).total_seconds() / 3600
            print(f"{i:<4} | {session.start_time.strftime('%Y-%m-%d %H:%M'):<20} | "
                  f"{session.end_time.strftime('%Y-%m-%d %H:%M'):<20} | {duration:.2f}")

    # --- SUPERVISION SESSIONS ---
    print(f"\n=== Supervision Sessions for {display_month}/{display_year} ===")
    if not filtered_supervision:
        print("No supervision sessions recorded.")
    else:
        print(f"{'ID':<4} | {'Start Time':<20} | {'End Time':<20} | {'Format':<10} | {'Type':<10} | {'Direct Obs'}")
        print("-" * 68)
        for i, session in enumerate(filtered_supervision, start=1):
            fmt = session.format.name
            stype = session.session_type.name
            obs = "YES" if session.is_direct_observation else "NO"
            print(f"{i:<4} | {session.start_time.strftime('%Y-%m-%d %H:%M'):<20} | "
                  f"{session.end_time.strftime('%Y-%m-%d %H:%M'):<20} | {fmt:<10} | {stype:<10} | {obs}")

    # --- TOTALS ---
    print(f"\n--- Monthly Totals ---")
    print(f"Work Hours:            {work_hours:.2f}")
    print(f"Supervision Hours:     {superv_hours:.2f}")
    input("\nPress Enter to return to menu...")


def generate_compliance_report(work_sessions, supervision_sessions, year, month):
    filtered_work = sessions_in_month(work_sessions, year, month)
    filtered_superv = sessions_in_month(supervision_sessions, year, month)
    work_hours = total_hours(filtered_work)
    superv_hours = total_hours(filtered_superv)
    required_hours = work_hours * .05

    if work_hours == 0 or required_hours == 0:
        percent_achieved = 0
    else:
        percent_achieved = min((superv_hours / required_hours) * 100, 100)

    hours_still_needed = required_hours - superv_hours
    if hours_still_needed < 0:
        hours_still_needed = 0

    return {
        'is_compliant': is_compliant(work_sessions, supervision_sessions, year, month),
        'has_individual': has_individual_session(filtered_superv),
        'has_direct_observation': has_direct_observation(filtered_superv),
        'work_hours': work_hours,
        'supervised_hours': superv_hours,
        'required_hours': required_hours,
        'percent_achieved': percent_achieved,
        'hours_still_needed': hours_still_needed
    }

def view_year_summary():
    year_input = input("Enter year (e.g., 2026): ").strip()
    try:
        year_val = int(year_input)
    except ValueError:
        print("Invalid input. Please enter a valid year.")
        return
    for month in range(1, 13):
        report = generate_compliance_report(sessions, supervision_sessions, year_val, month)
        if report['work_hours'] > 0:
            print(f"\n=== Compliance Report for {month}/{year_val} ===")
            print(f"Is Compliant (5% rule):    {report['is_compliant']}")
            print(f"Has Individual Session:    {report['has_individual']}")
            print(f"Has Direct Observation:    {report['has_direct_observation']}")


if __name__ == "__main__":
    main_menu()
