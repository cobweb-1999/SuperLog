# =============================================================================
# SUPERLOG - RBT Supervision Hour Tracker
# =============================================================================

import enum
import datetime as dt
import json
from datetime import datetime


class ObservationType(enum.Enum):
    IN_PERSON = 1
    REMOTE = 0


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1
    GROUP = 0


class WorkSession:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


class SupervisionSession:
    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        self.start_time = start_time
        self.end_time = end_time
        self.format = format
        self.session_type = session_type
        self.is_direct_observation = is_direct_observation


# --- sample data (unchanged from before) ---
monday_session = WorkSession(dt.datetime(2026, 7, 6, 9, 30), dt.datetime(2026, 7, 6, 12, 30))
tuesday_session = WorkSession(dt.datetime(2026, 7, 7, 9, 30), dt.datetime(2026, 7, 7, 12, 30))
wednesday_session = WorkSession(dt.datetime(2026, 7, 8, 9, 30), dt.datetime(2026, 7, 8, 12, 30))
thursday_session = WorkSession(dt.datetime(2026, 7, 9, 9, 30), dt.datetime(2026, 7, 9, 12, 30))
friday_session = WorkSession(dt.datetime(2026, 7, 10, 9, 30), dt.datetime(2026, 7, 10, 12, 30))

supervision_session_monday = SupervisionSession(
    dt.datetime(2026, 7, 6, 9, 30), dt.datetime(2026, 7, 6, 12, 30),
    ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True
)
supervision_session_tuesday = SupervisionSession(
    dt.datetime(2026, 7, 7, 9, 30), dt.datetime(2026, 7, 7, 12, 30),
    ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True
)
supervision_session_wednesday = SupervisionSession(
    dt.datetime(2026, 7, 8, 9, 30), dt.datetime(2026, 7, 8, 12, 30),
    ObservationType.IN_PERSON, SupervisionType.INDIVIDUAL, True
)
supervision_session_thursday = SupervisionSession(
    dt.datetime(2026, 7, 9, 9, 30), dt.datetime(2026, 7, 9, 12, 30),
    ObservationType.IN_PERSON, SupervisionType.GROUP, False
)
supervision_session_friday = SupervisionSession(
    dt.datetime(2026, 7, 10, 9, 30), dt.datetime(2026, 7, 10, 12, 30),
    ObservationType.IN_PERSON, SupervisionType.GROUP, False
)

supervision_sessions = [
    supervision_session_monday, supervision_session_tuesday, supervision_session_wednesday,
    supervision_session_thursday, supervision_session_friday
]
sessions = [monday_session, tuesday_session, wednesday_session, thursday_session, friday_session]

class Week:
    def __init__(self, name, start_day, end_day, work_sessions, supervision_sessions):
            self.name = name
            self.start_day = start_day
            self.end_day = end_day
            self.work_sessions = work_sessions
            self.supervision_sessions = supervision_sessions
    def total_work_hours(self):
            return total_hours(self.work_sessions)
    def total_supervision_hours(self):
            return total_hours(self.supervision_sessions)

weeks_data = [
    ("Week_One", dt.datetime(2026, 7, 1), dt.datetime(2026, 7, 7)),
    ("Week_Two", dt.datetime(2026, 7, 8), dt.datetime(2026, 7, 14)),
    ("Week_Three", dt.datetime(2026, 7, 15), dt.datetime(2026, 7, 21)),
    ("Week_Four", dt.datetime(2026, 7, 22), dt.datetime(2026, 7, 28)),
]

weeks_objects = []
for name, start_day, end_day in weeks_data:
        name, start_day, end_day
        week = Week(name, start_day, end_day, sessions, supervision_sessions)
        weeks_objects.append(week)


def total_hours(session_list):
    total = 0
    for session in session_list:
        gap = session.end_time - session.start_time
        total = total + (gap.total_seconds() / 3600)
    return total


def sessions_in_month(session_list, year, month):
    return [session for session in session_list if session.start_time.year == year and session.start_time.month == month]


def is_compliant(work_sessions, supervision_sessions, year, month):
    filtered_work_sessions = sessions_in_month(work_sessions, year, month)
    filtered_supervision_sessions = sessions_in_month(supervision_sessions, year, month)
    required_hours = total_hours(filtered_work_sessions) * .05
    return total_hours(filtered_supervision_sessions) >= required_hours


def has_individual_session(supervision_sessions):
    found = False
    for session in supervision_sessions:
        if session.session_type == SupervisionType.INDIVIDUAL:
            found = True
    return found


def has_direct_observation(supervision_sessions):
    found = False
    for session in supervision_sessions:
        if session.is_direct_observation:
            found = True
    return found


def generate_compliance_report(work_sessions, supervision_sessions, year, month):
    compliant = is_compliant(work_sessions, supervision_sessions, year, month)
    individual = has_individual_session(sessions_in_month(supervision_sessions, year, month))
    observation = has_direct_observation(sessions_in_month(supervision_sessions, year, month))
    
    return {
        'is_compliant': compliant,
        'has_individual': individual,
        'has_direct_observation': observation
    }


# -----------------------------------------------------------------------------
# WorkSession <-> dict
# -----------------------------------------------------------------------------
def work_session_to_dict(session):
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat()
    }


def dict_to_work_session(data):
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    return WorkSession(start_time, end_time)


# -----------------------------------------------------------------------------
# SupervisionSession <-> dict
# -----------------------------------------------------------------------------
def supervision_sessions_to_dict(supervision_session):
    return {
        'start_time': supervision_session.start_time.isoformat(),
        'end_time': supervision_session.end_time.isoformat(),
        'format': supervision_session.format.value,
        'session_type': supervision_session.session_type.value,
        'is_direct_observation': supervision_session.is_direct_observation
    }


def dict_to_supervision_sessions(data):
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    format = ObservationType(data['format'])
    session_type = SupervisionType(data['session_type'])
    is_direct_observation = data['is_direct_observation']
    return SupervisionSession(start_time, end_time, format, session_type, is_direct_observation)


# --- Test Code ---
work_session_as_dict = [work_session_to_dict(session) for session in sessions]

with open('work_sessions.json', 'w') as file:
    json.dump(work_session_as_dict, file, indent=4)

with open('work_sessions.json', 'r') as file:
    loaded_work_data = json.load(file)

loaded_work_sessions = [dict_to_work_session(entry) for entry in loaded_work_data]

supervision_sessions_as_dicts = [supervision_sessions_to_dict(s) for s in supervision_sessions]

with open('supervision_sessions.json', 'w') as file:
    json.dump(supervision_sessions_as_dicts, file, indent=4)

with open('supervision_sessions.json', 'r') as file:
    loaded_supervision_data = json.load(file)

loaded_supervision_sessions = [dict_to_supervision_sessions(entry) for entry in loaded_supervision_data]

print("Superlog is starting...")
print(total_hours(loaded_supervision_sessions))                    # expect 15.0
print(has_individual_session(loaded_supervision_sessions))         # expect True
print(has_direct_observation(loaded_supervision_sessions))         # expect True
print(loaded_supervision_sessions[0].format)                       # expect ObservationType.IN_PERSON
print(total_hours(loaded_work_sessions))
print(len(sessions_in_month(sessions, 2026, 7)))
print(weeks_objects[0].name)
print(weeks_objects[0].total_work_hours())
print(weeks_objects[0].total_supervision_hours())
print(is_compliant(sessions, supervision_sessions, 2026, 7))
print("Compliance Report for July 2026:")
print(generate_compliance_report(sessions, supervision_sessions, 2026, 7))
