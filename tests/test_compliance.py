import datetime as dt
import unittest

import main as core


class ComplianceTest(unittest.TestCase):
    def test_compliance(self):
        work_sessions = [
            core.WorkSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
            )
        ]

        supervision_sessions = [
            core.SupervisionSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
                core.ObservationType.IN_PERSON,
                core.SupervisionType.INDIVIDUAL,
                True,
            )
        ]

        report = core.generate_compliance_report(
            work_sessions,
            supervision_sessions,
            2026,
            9,
        )

        self.assertTrue(report['meets_five_percent'])
        self.assertTrue(report['has_individual'])
        self.assertTrue(report['is_compliant'])
        self.assertTrue(report['has_direct_observation'])

    def test_below_five_percent(self):
        work_sessions = [
            core.WorkSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
            )
        ]
        supervision_sessions = [
            core.SupervisionSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 8, 15),
                core.ObservationType.IN_PERSON,
                core.SupervisionType.INDIVIDUAL,
                True,
            )
        ]

        report = core.generate_compliance_report(
            work_sessions,
            supervision_sessions,
            2026,
            9,
        )

        self.assertFalse(report['meets_five_percent'])
        self.assertTrue(report['has_individual'])
        self.assertTrue(report['has_direct_observation'])
        self.assertFalse(report['is_compliant'])

    def test_missing_individual_supervision(self):
        work_sessions = [
            core.WorkSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
            )
        ]
        supervision_sessions = [
            core.SupervisionSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
                core.ObservationType.IN_PERSON,
                core.SupervisionType.GROUP,
                True,
            )
        ]

        report = core.generate_compliance_report(
            work_sessions,
            supervision_sessions,
            2026,
            9,
        )

        self.assertTrue(report['meets_five_percent'])
        self.assertFalse(report['has_individual'])
        self.assertTrue(report['has_direct_observation'])
        self.assertFalse(report['is_compliant'])

    def test_missing_direct_observation(self):
        work_sessions = [
            core.WorkSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
            )
        ]
        supervision_sessions = [
            core.SupervisionSession(
                dt.datetime(2026, 9, 1, 8, 0),
                dt.datetime(2026, 9, 1, 18, 0),
                core.ObservationType.REMOTE,
                core.SupervisionType.INDIVIDUAL,
                False,
            )
        ]

        report = core.generate_compliance_report(
            work_sessions,
            supervision_sessions,
            2026,
            9,
        )

        self.assertTrue(report['meets_five_percent'])
        self.assertTrue(report['has_individual'])
        self.assertFalse(report['has_direct_observation'])
        self.assertFalse(report['is_compliant'])

    def test_back_to_back_sessions_do_not_overlap(self):
        first = core.WorkSession(
            dt.datetime(2026, 9, 1, 9, 0),
            dt.datetime(2026, 9, 1, 10, 0),
        )
        second = core.WorkSession(
            dt.datetime(2026, 9, 1, 10, 0),
            dt.datetime(2026, 9, 1, 11, 0),
        )

        self.assertFalse(core.sessions_overlap(first, second))

    def test_overlapping_sessions_are_rejected(self):
        first = core.WorkSession(
            dt.datetime(2026, 9, 1, 9, 0),
            dt.datetime(2026, 9, 1, 10, 0),
        )
        second = core.WorkSession(
            dt.datetime(2026, 9, 1, 9, 30),
            dt.datetime(2026, 9, 1, 10, 30),
        )

        self.assertTrue(core.sessions_overlap(first, second))

if __name__ == '__main__':
    unittest.main()

    