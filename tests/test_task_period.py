import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/daily-planner/scripts/task_period.py'
SPEC = importlib.util.spec_from_file_location('task_period', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TaskPeriodTests(unittest.TestCase):
    def compute(self, deadline, start=None, now='2026-10-15T12:00:00+08:00'):
        return MODULE.compute_period(now, deadline, start)

    def test_exactly_one_day_is_not_eligible(self):
        self.assertFalse(self.compute('2026-10-16T12:00:00+08:00')['eligible'])

    def test_more_than_one_day_is_eligible(self):
        result = self.compute('2026-10-16T12:00:01+08:00')
        self.assertTrue(result['eligible'])
        self.assertEqual((result['start_date'], result['end_date']), ('2026-10-15', '2026-10-17'))

    def test_same_day_deadline_has_no_calendar_period(self):
        self.assertFalse(self.compute('2026-10-15')['eligible'])

    def test_date_deadline_includes_whole_last_day(self):
        result = self.compute('2026-10-18')
        self.assertEqual((result['start_date'], result['end_date']), ('2026-10-15', '2026-10-19'))
        self.assertEqual(result['transparency'], 'transparent')
        self.assertTrue(result['deadline_time'].startswith('2026-10-18T23:59:59'))

    def test_next_day_date_uses_end_of_day(self):
        self.assertTrue(self.compute('2026-10-16')['eligible'])

    def test_utc_deadline_converts_before_choosing_calendar_date(self):
        result = self.compute('2026-10-18T18:00:00Z')
        self.assertEqual(result['end_date'], '2026-10-20')
        self.assertEqual(result['deadline_time'], '2026-10-19T02:00:00+08:00')

    def test_explicit_start_is_preserved(self):
        result = self.compute('2026-10-20', '2026-10-18')
        self.assertEqual(result['start_date'], '2026-10-18')

    def test_explicit_short_window_has_no_period(self):
        self.assertFalse(self.compute('2026-10-20T17:00:00+08:00', '2026-10-20T09:00:00+08:00')['eligible'])

    def test_overdue_task_does_not_create_inverted_event(self):
        result = self.compute('2026-10-14')
        self.assertTrue(result['overdue'])
        self.assertFalse(result['eligible'])
        self.assertIsNone(result['start_date'])

    def test_invalid_start_range_raises(self):
        with self.assertRaises(ValueError):
            self.compute('2026-10-16', '2026-10-18')

    def test_ambiguous_current_timezone_raises(self):
        with self.assertRaises(ValueError):
            self.compute('2026-10-18', now='2026-10-15T12:00:00')

    def test_cli_emits_expected_all_day_dates(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--now', '2026-10-15T12:00:00+08:00', '--deadline', '2026-10-18'], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['end_date'], '2026-10-19')

    def display(self, **kwargs):
        return MODULE.compute_task_display('2026-10-15T12:00:00+08:00', **kwargs)

    def test_short_task_also_has_calendar_entry(self):
        events = self.display(deadline='2026-10-15T17:00:00+08:00')['events']
        self.assertEqual([(x['type'], x['start_date'], x['end_date']) for x in events], [('date_task', '2026-10-15', '2026-10-16')])

    def test_undated_task_uses_capture_day_without_inventing_due(self):
        result = self.display()
        self.assertEqual(result['events'][0]['date_source'], 'capture_day')
        self.assertEqual(result['events'][0]['start_date'], '2026-10-15')
        self.assertFalse(result['invented_todoist_due_date'])

    def test_planned_day_overrides_short_deadline_day(self):
        event = self.display(deadline='2026-10-16T11:00:00+08:00', planned_date='2026-10-15')['events'][0]
        self.assertEqual(event['date_source'], 'planned_date')
        self.assertEqual(event['start_date'], '2026-10-15')

    def test_planned_day_without_deadline_has_calendar_entry(self):
        events = self.display(planned_date='2026-10-21')['events']
        self.assertEqual(events[0]['start_date'], '2026-10-21')
        self.assertEqual(events[0]['type'], 'date_task')

    def test_long_task_and_execution_have_distinct_entries(self):
        events = self.display(deadline='2026-10-18', execution_start='2026-10-16T19:00:00+08:00', execution_end='2026-10-16T21:00:00+08:00')['events']
        self.assertEqual([e['type'] for e in events], ['period', 'execution'])

    def test_execution_avoids_redundant_single_day_task_entry(self):
        events = self.display(execution_start='2026-10-15T19:00:00+08:00', execution_end='2026-10-15T21:00:00+08:00')['events']
        self.assertEqual([e['type'] for e in events], ['execution'])

    def test_incomplete_execution_needs_missing_end(self):
        with self.assertRaises(ValueError):
            self.display(execution_start='2026-10-15T19:00:00+08:00')

    def test_reversed_execution_is_rejected(self):
        with self.assertRaises(ValueError):
            self.display(execution_start='2026-10-15T21:00:00+08:00', execution_end='2026-10-15T19:00:00+08:00')

    def test_display_cli_accepts_undated_task(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--display', '--now', '2026-10-15T12:00:00+08:00'], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['events'][0]['type'], 'date_task')


if __name__ == '__main__':
    unittest.main()
