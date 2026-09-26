"""Read-only Cold DM prompt snapshot tests; no live database or sending."""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules"))
import tracker
from test_cold_dm_dashboard import Database


class ColdDmPromptBatchTests(unittest.TestCase):
    def test_includes_current_note_with_exact_tracker_mapping(self):
        apps = [
            {"id": 31, "company": "TrueMeds Fixture", "role": "AI Engineer",
             "url": "https://jobs.test/54222", "status": "Applied", "follow_up_date": "2026-09-27"},
            {"id": 32, "company": "Stale Fixture", "role": "ML Engineer",
             "url": "https://jobs.test/66", "status": "Applied", "follow_up_date": "2026-09-26"},
            {"id": 33, "company": "Unmatched Fixture", "role": "Researcher",
             "url": "https://jobs.test/deleted", "status": "Applied", "follow_up_date": "2026-09-26"},
            {"id": 34, "company": "Wrong Company", "role": "Engineer",
             "url": "https://jobs.test/88", "status": "Applied", "follow_up_date": "2026-09-26"},
        ]
        jobs = [
            {"id": 54222, "company": "TrueMeds Fixture", "title": "AI Engineer", "location": "KA, IN",
             "source": "Indeed", "url": "https://jobs.test/54222"},
            {"id": 66, "company": "Stale Fixture", "title": "ML Engineer", "location": "", "source": "LinkedIn", "url": "https://jobs.test/66"},
            {"id": 88, "company": "Impostor", "title": "Engineer", "location": "", "source": "Other", "url": "https://jobs.test/88"},
        ]
        messages = [
            {"scraped_job_id": 54222, "message_type": "screen", "content": "pass: Verified Python overlap",
             "is_stale": False, "profile_version": 5},
            {"scraped_job_id": 54222, "message_type": "cold_dm", "content": "Hello — real voice agent work.",
             "is_stale": False, "profile_version": 5, "generated_at": "2026-09-26T18:00:00Z"},
            {"scraped_job_id": 66, "message_type": "screen", "content": "pass: Old screening",
             "is_stale": True, "profile_version": 4},
            {"scraped_job_id": 66, "message_type": "cold_dm", "content": "Old résumé message",
             "is_stale": False, "profile_version": 4},
            {"scraped_job_id": 88, "message_type": "screen", "content": "pass: Potential match",
             "is_stale": False, "profile_version": 5},
            {"scraped_job_id": 88, "message_type": "cold_dm", "content": "Impostor note",
             "is_stale": False, "profile_version": 5},
        ]
        db = Database(apps, jobs, messages)
        with patch.object(tracker, "_get_client", return_value=db), patch.object(
            tracker, "_user_now", return_value=datetime.fromisoformat("2026-09-27T12:00:00+05:30")
        ):
            batch = tracker.get_cold_dm_prompt_jobs(resume_version=5)
        self.assertEqual([(item["tracker_id"], item["job_id"]) for item in batch],
                         [(32, 66), (33, None), (34, None), (31, 54222)])
        self.assertIsInstance(batch[-1]["job_id"], int)
        ready = batch[-1]
        self.assertEqual((ready["title"], ready["location"], ready["source"]),
                         ("AI Engineer", "KA, IN", "Indeed"))
        self.assertNotIn("screening_status", ready)
        self.assertNotIn("screening_reason", ready)
        self.assertEqual((ready["cold_dm"], ready["blocked_reason"]),
                         ("Hello — real voice agent work.", ""))
        self.assertNotIn("screening_status", batch[0])
        self.assertIsNone(batch[0]["cold_dm"])
        self.assertIn("No current Cold DM", batch[0]["blocked_reason"])
        self.assertTrue(all(item["cold_dm"] is None for item in batch[1:3]))
        self.assertEqual(db.queries.count("job_messages"), 1)

    def test_already_tracked_due_followup_uses_current_note_without_new_job_screen(self):
        db = Database([{"id": 1, "company": "Fixture", "role": "Engineer", "url": "https://jobs.test/1",
                        "status": "Applied", "follow_up_date": "2026-09-27"}],
                      [{"id": 2, "company": "Fixture", "title": "Engineer", "location": "", "source": "Indeed",
                        "url": "https://jobs.test/1"}],
                      [{"scraped_job_id": 2, "message_type": "cold_dm", "content": "Saved note",
                        "is_stale": False, "profile_version": 5}])
        with patch.object(tracker, "_get_client", return_value=db), patch.object(
            tracker, "_user_now", return_value=datetime.fromisoformat("2026-09-27T12:00:00+05:30")
        ):
            batch = tracker.get_cold_dm_prompt_jobs(5)
        self.assertNotIn("screening_status", batch[0])
        self.assertEqual(batch[0]["blocked_reason"], "")
        self.assertEqual(batch[0]["cold_dm"], "Saved note")
        self.assertEqual(db.queries.count("job_messages"), 1)

    def test_more_than_limit_fails_before_reading_note_data(self):
        db = Database([{"id": i, "company": "Fixture", "role": "Engineer", "url": "",
                        "status": "Applied", "follow_up_date": "2026-09-27"} for i in range(2)], [], [])
        with patch.object(tracker, "_get_client", return_value=db), patch.object(
            tracker, "_user_now", return_value=datetime.fromisoformat("2026-09-27T12:00:00+05:30")
        ):
            with self.assertRaisesRegex(ValueError, "2 Cold DMs are due; the prompt limit is 1"):
                tracker.get_cold_dm_prompt_jobs(5, limit=1)
        self.assertNotIn("job_messages", db.queries)


if __name__ == "__main__":
    unittest.main()
