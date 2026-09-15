import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULES = Path(__file__).resolve().parents[1] / "modules"
sys.path.insert(0, str(MODULES))

import cloud_connector as cc
from hourly import _resume_fit_filter

RUN_ID = "2026-09-15T06:59:00+05:30.a1b2c3d4"


def prepared():
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "kind": "items",
        "profile": "profile",
        "screen_jobs": [{"id": 11}],
        "outreach_jobs": [{"id": 12, "char_limit": 600}],
        "requests": [{"request_id": 13, "char_limit": 20, "prompt": "write"}],
        "followup_requests": [],
    }


def actions():
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "screens": [{"job_id": 11, "decision": "pass", "reason": "Strong fit"}],
        "outreach_drafts": [{"job_id": 12, "content": "Useful first sentence. " + "x" * 700}],
        "request_results": [{"request_id": 13, "status": "ready",
                             "content": "Fits in one sentence. This part is too long."}],
        "notification": {"title": "Hourly run", "body": "0 new jobs"},
    }


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

    def test_prepare_carries_run_id_and_builds_followup(self):
        context = {
            "schema_version": 1, "run_id": RUN_ID,
            "user_profile": {"resume_text": "Python AI " * 30},
            "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
            "due_applications": [{"id": 7, "company": "Acme", "role": "AI Engineer",
                                  "platform": "LinkedIn", "date_applied": "2026-09-01"}],
            "follow_up_history": [], "active_followup_requests": [],
            "completeness": {"follow_up_history": True,
                             "active_followup_requests": True},
        }
        out = cc.prepare_items(context)
        self.assertEqual(out["run_id"], RUN_ID)
        self.assertEqual(out["followup_requests"][0]["params"]["_application_id"], 7)

    def test_prepare_refuses_truncated_history_context(self):
        context = {
            "schema_version": 1, "run_id": RUN_ID, "user_profile": {},
            "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
            "due_applications": [], "follow_up_history": [],
            "active_followup_requests": [],
            "completeness": {"follow_up_history": False,
                             "active_followup_requests": True},
        }
        with self.assertRaisesRegex(ValueError, "not explicitly complete"):
            cc.prepare_items(context)

    def test_validation_enforces_limits_and_batch_membership(self):
        out = cc.validate_actions(prepared(), actions())
        self.assertLessEqual(len(out["request_results"][0]["content"]), 20)
        self.assertLessEqual(len(out["outreach_drafts"][0]["content"]), 600)
        self.assertEqual(out["outreach_drafts"][0].keys(), {"job_id", "content"})
        self.assertEqual(out["run_id"], RUN_ID)

        bad = actions()
        bad["screens"][0]["job_id"] = 999
        with self.assertRaisesRegex(ValueError, "outside the exported batch"):
            cc.validate_actions(prepared(), bad)

    def test_validation_rejects_duplicate_boolean_and_malformed_text(self):
        bad = actions()
        bad["screens"].append(dict(bad["screens"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            cc.validate_actions(prepared(), bad)

        bad = actions()
        bad["screens"][0]["job_id"] = True
        with self.assertRaisesRegex(ValueError, "booleans"):
            cc.validate_actions(prepared(), bad)

        bad = actions()
        bad["outreach_drafts"][0]["content"] = "bad\x00text"
        with self.assertRaisesRegex(ValueError, "control character"):
            cc.validate_actions(prepared(), bad)

        bad = actions()
        bad["request_results"][0]["content"] = "bad\ud800text"
        with self.assertRaisesRegex(ValueError, "control character"):
            cc.validate_actions(prepared(), bad)

        bad_prepared = prepared()
        bad_prepared["requests"][0]["char_limit"] = True
        with self.assertRaisesRegex(ValueError, "integer between"):
            cc.validate_actions(bad_prepared, actions())

    def test_validation_rejects_non_cold_dm_override(self):
        bad = actions()
        bad["outreach_drafts"][0]["message_type"] = "screen"
        with self.assertRaisesRegex(ValueError, "must be cold_dm"):
            cc.validate_actions(prepared(), bad)

    def test_notification_sql_dedups_by_run_and_stage(self):
        first = cc.validate_actions(prepared(), actions())
        sql = cc.render_sql(first)
        self.assertIn("metadata->>'run_id'", sql)
        self.assertIn("metadata->>'stage'", sql)
        self.assertNotIn("interval '2 hours'", sql)
        self.assertIn("'cold_dm'", sql)
        self.assertNotIn("coalesce(j->>'message_type'", sql)

        second = dict(first)
        second["run_id"] = "2026-09-15T07:59:00+05:30.a1b2c3d4"
        self.assertNotEqual(cc.render_sql(first), cc.render_sql(second))

    def test_sql_uses_base64_not_message_text(self):
        marker = "O'Reilly; DROP TABLE scraped_jobs; --"
        value = actions()
        value["outreach_drafts"][0]["content"] = marker
        plan = cc.validate_actions(prepared(), value)
        sql = cc.render_sql(plan)
        self.assertNotIn(marker, sql)
        self.assertIn("decode('", sql)

    @patch("scraper.check_apply_type", return_value="EASY_APPLY")
    @patch("scraper.run_all_scrapers")
    def test_scrape_reuses_filters_and_carries_run_id(self, run_all, _check):
        run_all.return_value = ([{
            "title": "AI Engineer", "company": "O'Reilly AI", "location": "India",
            "source": "LinkedIn AI/ML", "url": "https://example.test/1",
            "description": "Python RAG entry-level role — multilingual",
        }], {"LinkedIn AI/ML": 1}, {})
        context = {"schema_version": 1, "run_id": RUN_ID,
                   "existing_job_urls": [],
                   "user_profile": {"resume_text": "Python RAG AI " * 30},
                   "last_email_subject": "Job Alert #8"}
        with patch.dict(os.environ, {"APPLY_CHECK_DELAY_SECONDS": "0"}):
            out = cc.scrape_plan(context)
        self.assertEqual(out["run_id"], RUN_ID)
        self.assertEqual(out["email_log"]["subject"], "Job Alert #9")
        self.assertEqual(out["jobs"][0]["verdict"], "EASY_APPLY")


if __name__ == "__main__":
    unittest.main()
