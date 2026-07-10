import enum
import datetime as dt

# ENUMS: not covered directly in this playlist (it's a slightly more advanced
# topic), but conceptually related to the "constants" idea from early videos
# on variables - the difference is an Enum locks a variable to only a few
# valid named choices instead of letting it be any value.
class ObservationType(enum.Enum):
    IN_PERSON = 1
    REMOTE = 0


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1
    GROUP = 0


# CLASSES: this __init__ pattern, and the use of "self", is the core topic
# from the Classes videos in this playlist (the ones covering __init__,
# instance attributes, and "self" as the reference to the specific object
# being built). WorkSession is the simplest possible example of this - two
# attributes, no logic.
class WorkSession:  # Individual Day
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


# Same __init__/self pattern as WorkSession, just with more attributes.
# Notice every attribute follows the identical "self.x = x" shape - that's
# the pattern from the Classes videos, just repeated 5 times instead of 2.
class SupervisionSession:  # Individual Supervision
    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        self.start_time = start_time
        self.end_time = end_time
        self.format = format
        self.session_type = session_type
        self.is_direct_observation = is_direct_observation


# DATETIME: this is straight from the "Datetime Module" video in the
# playlist - constructing a datetime directly from year/month/day/hour/minute
# numbers, no string-parsing needed since we're typing the values directly.
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

# These three are deliberately identical in type (individual, in-person,
# observed) - representing a realistic week of consistent 1:1 supervision.
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

# These two are deliberately DIFFERENT (group, remote, not observed) - this
# is the variation needed to later test "does at least one individual
# session exist" logic without it trivially passing on identical data.
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

# LISTS: from the Lists/Tuples video - a plain list holding multiple objects,
# so a loop can process all of them together instead of one at a time.
supervision_sessions = [
    supervision_session_monday,
    supervision_session_tuesday,
    supervision_session_wednesday,
    supervision_session_thursday,
    supervision_session_friday
]
sessions = [monday_session, tuesday_session, wednesday_session, thursday_session, friday_session]


# FUNCTIONS + FOR LOOPS: this whole function is a direct combination of the
# "Functions" video (def, parameters, return) and the "Loops and Iterations"
# video (for x in list). Note this function only touches session.start_time
# and session.end_time - it never checks what class the object actually is.
# That's why it works on BOTH WorkSession and SupervisionSession below,
# even though we only wrote it once. This is the "reuse" concept from
# Step 1 today - functions built around shared attributes work across
# different classes, as long as those classes have matching attribute names.
def total_hours(session_list):
    total = 0
    for session in session_list:
        gap = session.end_time - session.start_time
        hours_this_session = gap.total_seconds() / 3600
        total = total + hours_this_session
    return total


print("Superlog is starting...")
print(total_hours(supervision_sessions))  # expect 15.0 -> five 3-hour supervision sessions
print(total_hours(sessions))              # expect 15.0 -> five 3-hour work sessions