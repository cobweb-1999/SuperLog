# =============================================================================
# SUPERLOG - RBT Supervision Hour Tracker
# A tool to help Registered Behavior Technicians track compliance with the
# BACB requirement that at least 5% of monthly direct service hours be
# supervised, including at least one individual (not group) contact and
# at least one direct observation session per month.
# =============================================================================

import enum          # lets us define a fixed set of named choices (see below)
import datetime as dt # lets us work with real calendar dates and times
import json           # lets us save/load data to and from plain text files


# -----------------------------------------------------------------------------
# ENUMS - fixed, named choices
# -----------------------------------------------------------------------------
# An Enum locks a value to only a few valid options, instead of letting it be
# any arbitrary string or number. This prevents bugs like accidentally typing
# "in-preson" and silently breaking compliance logic - Python would catch that
# as an invalid reference instead of quietly accepting bad data.

class ObservationType(enum.Enum):
    IN_PERSON = 1
    REMOTE = 0


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1
    GROUP = 0


# -----------------------------------------------------------------------------
# CLASSES - the "nouns" of the app, modeling real-world things
# -----------------------------------------------------------------------------
# Every class here follows the same core pattern: __init__ runs automatically
# whenever a new object is created, and "self" refers to THIS specific object
# being built (as opposed to any other WorkSession/SupervisionSession that
# might also exist). Each attribute is just "self.name = name" - storing
# whatever was passed in, with no extra logic mixed in. Keeping these classes
# as pure data (no rule-checking inside them) means the compliance RULES can
# change later without ever having to touch these class definitions.

class WorkSession:  # Represents one day/shift of direct client service work
    def __init__(self, start_time, end_time):
        self.start_time = start_time   # a real datetime object
        self.end_time = end_time       # a real datetime object


class SupervisionSession:  # Represents one BCBA/RBT supervision contact
    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        self.start_time = start_time
        self.end_time = end_time
        self.format = format                      # ObservationType.IN_PERSON or .REMOTE
        self.session_type = session_type          # SupervisionType.INDIVIDUAL or .GROUP
        self.is_direct_observation = is_direct_observation  # True/False - was RBT directly observed?


# -----------------------------------------------------------------------------
# SAMPLE DATA - a realistic test week
# -----------------------------------------------------------------------------
# Real datetime objects are built directly from year/month/day/hour/minute -
# no string parsing needed since we're typing the numbers ourselves here.
# This block currently stands in for what will eventually come from user
# input or a saved file - it's just here to prove the logic works.

monday_session = WorkSession(
    start_time=dt.datetime(2026, 7, 6, 9, 30),
    end_time=dt.datetime(2026, 7, 6, 12, 30)
)

tuesday_session = WorkSession(
    start_time=dt.datetime(2026, 7, 7, 9, 30),
    end_time=dt.datetime(2026, 7, 7, 12, 30)
)

wednesday_session = WorkSession(
    start_time=dt.datetime(2026, 7, 8, 9, 30),
    end_time=dt.datetime(2026, 7, 8, 12, 30)
)

thursday_session = WorkSession(
    start_time=dt.datetime(2026, 7, 9, 9, 30),
    end_time=dt.datetime(2026, 7, 9, 12, 30)
)

friday_session = WorkSession(
    start_time=dt.datetime(2026, 7, 10, 9, 30),
    end_time=dt.datetime(2026, 7, 10, 12, 30)
)

# Monday/Tuesday/Wednesday are deliberately IDENTICAL in type
# (individual, in-person, observed) - representing a realistic week of
# consistent 1:1 supervision.
supervision_session_monday = SupervisionSession(
    start_time=dt.datetime(2026, 7, 6, 9, 30),
    end_time=dt.datetime(2026, 7, 6, 12, 30),
    format=ObservationType.IN_PERSON,
    session_type=SupervisionType.INDIVIDUAL,
    is_direct_observation=True
)

supervision_session_tuesday = SupervisionSession(
    start_time=dt.datetime(2026, 7, 7, 9, 30),
    end_time=dt.datetime(2026, 7, 7, 12, 30),
    format=ObservationType.IN_PERSON,
    session_type=SupervisionType.INDIVIDUAL,
    is_direct_observation=True
)

supervision_session_wednesday = SupervisionSession(
    start_time=dt.datetime(2026, 7, 8, 9, 30),
    end_time=dt.datetime(2026, 7, 8, 12, 30),
    format=ObservationType.IN_PERSON,
    session_type=SupervisionType.INDIVIDUAL,
    is_direct_observation=True
)

# Thursday/Friday are deliberately DIFFERENT (group, not observed) - this
# variation exists on purpose, so the "does at least one individual/observed
# session exist" checks below can be proven correct rather than trivially
# passing on a dataset where everything is identical.
supervision_session_thursday = SupervisionSession(
    start_time=dt.datetime(2026, 7, 9, 9, 30),
    end_time=dt.datetime(2026, 7, 9, 12, 30),
    format=ObservationType.IN_PERSON,
    session_type=SupervisionType.GROUP,
    is_direct_observation=False,
)

supervision_session_friday = SupervisionSession(
    start_time=dt.datetime(2026, 7, 10, 9, 30),
    end_time=dt.datetime(2026, 7, 10, 12, 30),
    format=ObservationType.IN_PERSON,
    session_type=SupervisionType.GROUP,
    is_direct_observation=False,
)

# LISTS - plain Python lists holding multiple objects together, so a loop
# can process all of them as a group instead of one at a time.
supervision_sessions = [
    supervision_session_monday,
    supervision_session_tuesday,
    supervision_session_wednesday,
    supervision_session_thursday,
    supervision_session_friday
]
sessions = [monday_session, tuesday_session, wednesday_session, thursday_session, friday_session]


# -----------------------------------------------------------------------------
# CORE LOGIC FUNCTIONS - the "verbs" of the app
# -----------------------------------------------------------------------------

def total_hours(session_list):
    """
    Adds up the total hours across a list of sessions.

    IMPORTANT: this function only ever touches session.start_time and
    session.end_time - it never checks what CLASS the object is. That's why
    the exact same function works on both WorkSession objects and
    SupervisionSession objects below, even though we only wrote it once.
    Functions built around shared attributes can operate across different
    classes, as long as those classes have matching attribute names.
    """
    total = 0  # running total, starts at zero before we've looked at anything
    for session in session_list:
        gap = session.end_time - session.start_time         # a timedelta object
        hours_this_session = gap.total_seconds() / 3600     # convert to plain hours
        total = total + hours_this_session
    return total


def is_compliant(work_sessions, supervision_sessions):
    """
    *Checks BACB Rule*: were at least 5% of worked hours supervised?
    Uses >= (not just >) because meeting the requirement EXACTLY should
    still count as compliant, not fail by one operator.
    """
    work_hours = total_hours(work_sessions)
    supervision_hours = total_hours(supervision_sessions)
    required_hours = work_hours * .05
    return supervision_hours >= required_hours


def has_individual_session(supervision_sessions):
    """
    *Checks BACB Rule Again*: at least one supervision contact INDIVIDUAL
    (not group)? Uses a "found flag" pattern - starts False, flips to True
    the moment a match is found, and stays True even if later sessions
    don't match. Returns False only if NO session ever matched.
    """
    found = False
    for session in supervision_sessions:
        if session.session_type == SupervisionType.INDIVIDUAL:
            found = True
    return found


def has_direct_observation(supervision_sessions):
    """
    *Checks BACB Rule for the third time*:  at least one supervision contact a DIRECT
    OBSERVATION session? Same "found flag" pattern as has_individual_session,
    just checking a different attribute (a plain boolean this time, so no
    Enum comparison needed - "if session.is_direct_observation:" already
    means "if this is True").
    """
    found = False
    for session in supervision_sessions:
        if session.is_direct_observation:
            found = True
    return found


# -----------------------------------------------------------------------------
# PERSISTENCE (Phase 4) - saving data so it survives after the program closes
# -----------------------------------------------------------------------------
# JSON can only store simple values: strings, numbers, True/False, lists, and
# dictionaries. It CANNOT store a WorkSession object or a datetime object
# directly - both need to be converted to something simpler first.

def work_session_to_dict(session):
    """
    Converts one WorkSession object into a plain dictionary that JSON can
    actually save. .isoformat() turns a datetime object into a plain text
    string (e.g. "2026-07-06T09:30:00") since raw datetime objects would
    crash json.dump() with a "not JSON serializable" error.
    """
    return {
        'start_time': session.start_time.isoformat(),
        'end_time': session.end_time.isoformat()
    }

def dict_to_work_sessions(data):
    start_time = data['start_time']
    end_time = data['end_time']
    start_time = dt.datetime.fromisoformat(start_time)
    end_time = dt.datetime.fromisoformat(end_time)
    return WorkSession(start_time, end_time)

with open('work_sessions.json', 'r') as f:
    loaded_data = json.load(f)

    test_sessions = dict_to_work_sessions(loaded_data[0])
# List comprehension: read right-to-left as "for each session in sessions,
# run work_session_to_dict(session), and collect all the results into a
# new list." Equivalent to a plain loop that appends to an empty list -
# this is just a shorter way to write that same idea.
sessions_as_dicts = [work_session_to_dict(session) for session in sessions]

# Opens (or creates) work_sessions.json in write mode and saves our list of
# dictionaries into it as real, human-readable JSON text. indent=4 just makes
# the file nicely formatted when opened - not required, but easier to read.
with open('work_sessions.json', 'w') as file:
    json.dump(sessions_as_dicts, file, indent=4)


# -----------------------------------------------------------------------------
# TEST OUTPUT - proving each piece works as expected
# -----------------------------------------------------------------------------
print("Superlog is starting...")
print(total_hours(supervision_sessions))  # expect 15.0 -> five 3-hour supervision sessions
print(total_hours(sessions))              # expect 15.0 -> five 3-hour work sessions
print(is_compliant(sessions, supervision_sessions))     # expect True  -> 15 hrs >> 0.75 hr requirement
print(has_direct_observation(supervision_sessions))     # expect True  -> Mon/Tue/Wed were observed
print(work_session_to_dict(monday_session))             # expect a dict with two ISO date strings
print(test_sessions.start_time)


# =============================================================================
# STILL TO BUILD (roadmap for future sessions):
# 1. dict_to_work_session(data) - the REVERSE of work_session_to_dict, turning
#    a loaded dictionary back into a real WorkSession object (needs
#    dt.datetime.fromisoformat() to reverse the .isoformat() conversion)
# 2. Use json.load() to read work_sessions.json back into Python at startup,
#    instead of always starting from the same 5 hardcoded sessions
# 3. A way to filter sessions by calendar month, since the 5% rule is
#    calculated per month, not as one giant lifetime total
# 4. User input (the input() function) so real data can be typed in, instead
#    of hardcoded in the file
# 5. Combine is_compliant / has_individual_session / has_direct_observation
#    into one master "full compliance report" function
# =============================================================================