import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULES = Path(__file__).resolve().parents[1] / "modules"
sys.path.insert(0, str(MODULES))

import cloud_connector as cc
from hourly import _resume_fit_filter


class CloudConnectorTests(unittest.TestCase):
    def test_profile_prefers_resume(self):
        resume = "R" * 220
        self.assertEqual(cc.profile_text({"resume_text": resume}), resume)

    def test_resume_filter_accepts_injected_profile(self):
        jobs = [{"title": "AI Engineer", "description": "Python RAG"}]
        kept, note = _resume_fit_filter(
            jobs,
            "Python RAG FastAPI LangChain ChromaDB SQL automation machine learning " * 3,
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("kept 1/1", note)

    def test_prepare_items_bounds_and_builds_followup(self):
        context = {
            "schema_version": 1,
            "user_profile": {"resume_text": "Python AI " * 30},
            "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
            "due_applications": [{"id": 7, "company": "Acme", "role": "AI Engineer", "platform": "LinkedIn", "date_applied": "2026-09-01"}],
            "follow_up_history": [], "active_followup_requests": [],
        }
        out = cc.prepare_items(context)
        self.assertEqual(out["followup_requests"][0]["params"]["_application_id"], 7)

    def test_actions_reject_empty_content(self):
        with self.assertRaises(ValueError):
            cc.validate_actions({"schema_version": 1, "screens": [], "outreach_drafts": [{"job_id": 1, "content": ""}], "request_results": []})

    def test_sql_uses_base64_not_message_text(self):
        marker = "O'Reilly; DROP TABLE scraped_jobs; --"
        plan = {"schema_version": 1, "kind": "actions", "screens": [],
                "outreach_drafts": [{"job_id": 2, "content": marker}],
                "request_results": [], "notification": None}
        sql = cc.render_sql(plan)
        self.assertNotIn(marker, sql)
        self.assertIn("decode('", sql)
        self.assertIn("ON CONFLICT", sql)

    @patch("scraper.check_apply_type", return_value="EASY_APPLY")
    @patch("scraper.run_all_scrapers")
    def test_scrape_reuses_filters_and_builds_plan(self, run_all, _check):
        run_all.return_value = ([{
            "title": "AI Engineer", "company": "Acme", "location": "India",
            "source": "LinkedIn AI/ML", "url": "https://example.test/1",
            "description": "Python RAG entry-level role",
        }], {"LinkedIn AI/ML": 1}, {})
        context = {"schema_version": 1, "existing_job_urls": [],
                   "user_profile": {"resume_text": "Python RAG AI " * 30},
                   "last_email_subject": "Job Alert #8"}
        with patch.dict(os.environ, {"APPLY_CHECK_DELAY_SECONDS": "0"}):
            out = cc.scrape_plan(context)
        self.assertEqual(out["email_log"]["subject"], "Job Alert #9")
        self.assertEqual(out["jobs"][0]["verdict"], "EASY_APPLY")


if __name__ == "__main__":
    unittest.main()
