"""Dashboard Cold DMs share the tracker's due schedule and stored draft state."""

import unittest
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules"))
import tracker


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.sort_column = None
        self.bounds = None

    def select(self, *_): return self

    def eq(self, column, value):
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def lte(self, column, value):
        self.filters.append(lambda row: row.get(column) is not None and row[column] <= value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def order(self, column):
        self.sort_column = column
        return self

    def range(self, start, end):
        self.bounds = (start, end)
        return self

    def execute(self):
        rows = [row for row in self.rows if all(test(row) for test in self.filters)]
        if self.sort_column:
            rows.sort(key=lambda row: row[self.sort_column])
        if self.bounds:
            rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


class Database:
    def __init__(self, applications, jobs, messages):
        self.rows = {"applications": applications, "scraped_jobs": jobs, "job_messages": messages}
        self.queries = []

    def table(self, name):
        query = Query(self.rows[name])
        self.queries.append(name)
        return query


class ColdDmDashboardTests(unittest.TestCase):
    def test_due_cards_map_to_exact_jobs_and_only_current_drafts_are_ready(self):
        apps = [
            {"id": 10, "company": "First", "role": "Engineer", "url": "https://jobs/one", "status": "Applied", "follow_up_date": "2026-09-26"},
            {"id": 11, "company": "Second", "role": "Researcher", "url": "https://jobs/two", "status": "Applied", "follow_up_date": "2026-09-27"},
            {"id": 12, "company": "Third", "role": "Analyst", "url": "https://jobs/three", "status": "Applied", "follow_up_date": "2026-09-27"},
            {"id": 13, "company": "Closed", "role": "Engineer", "url": "https://jobs/closed", "status": "Rejected", "follow_up_date": "2026-09-25"},
            {"id": 14, "company": "Future", "role": "Engineer", "url": "https://jobs/future", "status": "Applied", "follow_up_date": "2026-09-28"},
        ]
        jobs = [{"id": 901, "url": "https://jobs/one"}, {"id": 902, "url": "https://jobs/two"},
                {"id": 904, "url": "https://jobs/closed"}, {"id": 905, "url": "https://jobs/future"}]
        messages = [
            {"scraped_job_id": 901, "message_type": "cold_dm", "content": "Verified job-specific note", "is_stale": False},
            {"scraped_job_id": 902, "message_type": "cold_dm", "content": "Old resume note", "is_stale": True},
            {"scraped_job_id": 902, "message_type": "hr_email", "content": "Wrong type", "is_stale": False},
            {"scraped_job_id": 904, "message_type": "cold_dm", "content": "Closed", "is_stale": False},
            {"scraped_job_id": 905, "message_type": "cold_dm", "content": "Future", "is_stale": False},
        ]
        db = Database(apps, jobs, messages)
        with patch.object(tracker, "_get_client", return_value=db), patch.object(
            tracker, "_user_now", return_value=datetime.fromisoformat("2026-09-27T12:00:00+05:30")
        ):
            cards = tracker.get_cold_dm_todos()

        self.assertEqual([(row["id"], row["scraped_job_id"], row["cold_dm_ready"]) for row in cards],
                         [(10, 901, True), (11, 902, False), (12, None, False)])
        self.assertEqual(cards[0]["follow_up_date"], "2026-09-26")
        self.assertEqual(cards[1]["follow_up_date"], "2026-09-27")
        self.assertNotIn("content", cards[0])
        self.assertEqual(db.queries.count("job_messages"), 1)

    def test_empty_due_queue_does_not_query_drafts(self):
        db = Database([], [], [])
        with patch.object(tracker, "_get_client", return_value=db):
            self.assertEqual(tracker.get_cold_dm_todos(), [])
        self.assertNotIn("job_messages", db.queries)

    def test_due_cards_are_not_silently_cut_off_at_data_api_page_size(self):
        apps = [{"id": n, "company": "Fixture", "role": "Engineer", "url": "",
                 "status": "Applied", "follow_up_date": "2026-09-26"} for n in range(1, 1002)]
        apps[-1]["url"] = "https://jobs/last"
        db = Database(apps, [{"id": 7001, "url": "https://jobs/last"}], [
            {"scraped_job_id": 7001, "message_type": "cold_dm", "content": "Last page note", "is_stale": False},
        ])
        with patch.object(tracker, "_get_client", return_value=db):
            cards = tracker.get_cold_dm_todos()
        self.assertEqual(len(cards), 1001)
        self.assertEqual(cards[-1]["scraped_job_id"], 7001)
        self.assertTrue(cards[-1]["cold_dm_ready"])
        self.assertEqual(db.queries.count("applications"), 2)


if __name__ == "__main__":
    unittest.main()
