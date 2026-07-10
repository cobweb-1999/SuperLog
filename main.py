import enum
import datetime as dt


class ObservationType(enum.Enum):
    IN_PERSON = 1
    REMOTE = 0


class SupervisionType(enum.Enum):
    INDIVIDUAL = 1
    GROUP = 0


class WorkSession:  # Individual Day
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


class SupervisionSession:  # Individual Supervision
    def __init__(self, start_time, end_time, format, session_type, is_direct_observation):
        self.start_time = start_time
        self.end_time = end_time
        self.format = format
        self.session_type = session_type
        self.is_direct_observation = is_direct_observation


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

sessions = [monday_session, tuesday_session, wednesday_session, thursday_session, friday_session]


def total_hours(session_list):
    total = 0  # running total, starts at zero before we've looked at anything
    for session in session_list:
        # FIX 1: build the timedelta INSIDE the loop, using THIS session's
        # own start/end - not a leftover variable from earlier testing.
        gap = session.end_time - session.start_time

        # FIX 2: convert that one session's timedelta into a plain number
        # of hours (this is the same .total_seconds() / 3600 math you
        # already proved works by hand on a single session).
        hours_this_session = gap.total_seconds() / 3600

        # FIX 3: actually add it onto the running total - the previous
        # version computed this number and then threw it away.
        total = total + hours_this_session

    # FIX 4: return is now OUTSIDE the for loop (same indentation as "for"),
    # so it only fires after all 5 sessions have been added up - not after
    # just the first one.
    return total


print("Superlog is starting...")
print(total_hours(sessions))  # expect 15.0 -> five sessions x 3 hours each