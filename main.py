# =============================================================================
# SUPERLOG - RBT Supervision Hour Tracker
# =============================================================================

import enum
import datetime as dt
import json


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


def total_hours(session_list):
    total = 0
    for session in session_list:
        gap = session.end_time - session.start_time
        total = total + (gap.total_seconds() / 3600)
    return total


def is_compliant(work_sessions, supervision_sessions):
    required_hours = total_hours(work_sessions) * .05
    return total_hours(supervision_sessions) >= required_hours


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


# -----------------------------------------------------------------------------
# WorkSession <-> dict (already working from last session)
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
# SupervisionSession <-> dict (tonight's new work)
# -----------------------------------------------------------------------------
def supervision_sessions_to_dict(supervision_session):
    """
    Same shape as work_session_to_dict, but with 3 extra fields.
    - .isoformat() converts datetime -> string (2 fields need this)
    - .value converts an Enum member -> its plain number (2 fields need this,
      since JSON can't store an Enum member directly, only plain values)
    - is_direct_observation needs NO conversion - it's already a plain
      True/False, which JSON understands natively.
    """
    return {
        'start_time': supervision_session.start_time.isoformat(),
        'end_time': supervision_session.end_time.isoformat(),
        'format': supervision_session.format.value,
        'session_type': supervision_session.session_type.value,
        'is_direct_observation': supervision_session.is_direct_observation
    }


def dict_to_supervision_sessions(data):
    """
    The mirror image of supervision_sessions_to_dict, reversing each
    conversion in the opposite order:
    - fromisoformat() turns the two date strings back into real datetimes
    - EnumName(value) reconstructs an Enum member from its plain number -
      e.g. ObservationType(1) gives back ObservationType.IN_PERSON, the
      same member that .value turned into a 1 during saving.
    - is_direct_observation is pulled straight out, no conversion needed.
    - Builds and returns a real SupervisionSession, not a WorkSession -
      note ALL FIVE constructor arguments are supplied, in the same order
      as SupervisionSession.__init__ expects them.
    """
    start_time = dt.datetime.fromisoformat(data['start_time'])
    end_time = dt.datetime.fromisoformat(data['end_time'])
    format = ObservationType(data['format'])
    session_type = SupervisionType(data['session_type'])
    is_direct_observation = data['is_direct_observation']
    return SupervisionSession(start_time, end_time, format, session_type, is_direct_observation)


# -----------------------------------------------------------------------------
# Save/load round trip test
# -----------------------------------------------------------------------------
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
print(loaded_supervision_sessions[0].format)                       # expect ObservationType.IN_PERSON (a real Enum, not a number)


# =============================================================================
# STILL TO BUILD:
# 1. Do the same full save/load round trip for WorkSession (dict_to_work_session
#    already exists - just wire it through json.dump/json.load like above)
# 2. Filter sessions by calendar month before running compliance checks
# 3. Combine is_compliant / has_individual_session / has_direct_observation
#    into one master "full compliance report" function
# =============================================================================