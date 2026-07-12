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

import enum
import datetime as dt
import json


# =============================================================================
# ENUMS - fixed, named choices for supervision session attributes
# =============================================================================

class ObservationType(enum.Enum):
    IN_PERSON = 1
    REMOTE = 0


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1
    GROUP = 0


# =============================================================================
# CLASSES - data models
# =============================================================================

class WorkSession:
    """Represents one shift of direct client service work."""
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


class SupervisionSession:
    """Represents one BCBA/RBT supervision contact."""
    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
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

# These two lists hold the app's live, in-memory data. load_sessions() replaces
# their contents at startup; every menu action after that modifies them directly.
sessions = []
supervision_sessions = []


# =============================================================================
# CORE COMPLIANCE LOGIC
# =============================================================================

def total_hours(session_list):
    """Sums hours across any list of sessions (works on both session types,
    since it only ever touches start_time/end_time)."""
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


def has_direct_observation(supervision_sessions):
    """BACB Rule: at least one supervision contact included direct observation."""
    found = False
    for session in supervision_sessions:
        if session.is_direct_observation:
            found = True
    return found


def generate_compliance_report(work_sessions, supervision_sessions, year, month):
    """Bundles all three BACB compliance checks for a given month into one result."""
    month_supervision = sessions_in_month(supervision_sessions, year, month)
    return {
        'is_compliant': is_compliant(work_sessions, supervision_sessions, year, month),
        'has_individual': has_individual_session(month_supervision),
        'has_direct_observation': has_direct_observation(month_supervision)
    }


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


def load_sessions():
    """Loads sessions from JSON files at startup. Falls back to sample data
    on a fresh install where no save files exist yet."""
    global sessions, supervision_sessions

    try:
        with open('work_sessions.json', 'r') as file:
            work_data = json.load(file)
            sessions = [dict_to_work_session(entry) for entry in work_data]
    except FileNotFoundError:
        print("No saved work sessions found. Starting with sample data.")
        sessions = list(DEFAULT_WORK_SESSIONS)

    try:
        with open('supervision_sessions.json', 'r') as file:
            supervision_data = json.load(file)
            supervision_sessions = [dict_to_supervision_session(entry) for entry in supervision_data]
    except FileNotFoundError:
        print("No saved supervision sessions found. Starting with sample data.")
        supervision_sessions = list(DEFAULT_SUPERVISION_SESSIONS)


def save_sessions():
    """Saves the current in-memory sessions to their JSON files."""
    work_dicts = [work_session_to_dict(s) for s in sessions]
    with open('work_sessions.json', 'w') as file:
        json.dump(work_dicts, file, indent=4)

    supervision_dicts = [supervision_session_to_dict(s) for s in supervision_sessions]
    with open('supervision_sessions.json', 'w') as file:
        json.dump(supervision_dicts, file, indent=4)


# =============================================================================
# MENU / USER INTERACTION
# =============================================================================

def log_work_session():
    print("Format: YYYY-MM-DD HH:MM")
    start_time = dt.datetime.fromisoformat(input("Start time: "))
    end_time = dt.datetime.fromisoformat(input("End time: "))
    sessions.append(WorkSession(start_time, end_time))
    save_sessions()
    print(f"Work session logged: {start_time} to {end_time}")


def log_supervision_session():
    print("Format: YYYY-MM-DD HH:MM")
    start_time = dt.datetime.fromisoformat(input("Start time: "))
    end_time = dt.datetime.fromisoformat(input("End time: "))

    format_choice = int(input("Format (1=IN_PERSON, 0=REMOTE): "))
    format_enum = ObservationType(format_choice)

    type_choice = int(input("Session type (1=INDIVIDUAL, 0=GROUP): "))
    session_type_enum = SupervisionType(type_choice)

    direct_obs = input("Direct observation? (yes/no): ").strip().lower() == "yes"

    supervision_sessions.append(
        SupervisionSession(start_time, end_time, format_enum, session_type_enum, direct_obs)
    )
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


def main_menu():
    load_sessions()  # pull in saved data (or sample data) before showing the menu

    while True:
        print("\n=== SUPERLOG Menu ===")
        print("1) Log a work session")
        print("2) Log a supervision session")
        print("3) View compliance report")
        print("4) Exit")

        choice = input("Enter your choice (1-4): ")

        if choice == "1":
            log_work_session()
        elif choice == "2":
            log_supervision_session()
        elif choice == "3":
            view_compliance()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main_menu()