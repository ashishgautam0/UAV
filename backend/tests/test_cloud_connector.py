import hashlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULES = Path(__file__).resolve().parents[1] / "modules"
sys.path.insert(0, str(MODULES))

import cloud_connector as cc
from hourly import _resume_fit_filter

RUN_ID = "2026-09-18T06:59:00+05:30.a1b2c3d4"
PROFILE_TEXT = "Python FastAPI PostgreSQL machine learning Docker APIs production systems. " * 4
PROFILE = {"id": 5, "version": 2, "status": "active", "source_kind": "pdf", "raw_text": PROFILE_TEXT}


def prepared(include_letter=True):
    letter = {"job_id": 14, "resume_profile_id": 5, "resume_version": 2,
              "jd_version": 1, "jd_hash": "a" * 64, "match_score": 94,
              "analysis_version": "explainable-match-v1",
              "rules_version": cc.COVER_LETTER_RULES_VERSION,
              "char_limit": 1200, "prompt": "grounded",
              "grounding_profile": PROFILE_TEXT,
              "job_description": "Python APIs for production systems"}
    return {"schema_version": 1, "run_id": RUN_ID, "kind": "items", "profile": PROFILE_TEXT,
            "screen_jobs": [{"id": 11, "profile_version": 2}],
            "outreach_jobs": [{"id": 12, "profile_version": 2, "char_limit": 600}],
            "requests": [{"request_id": 13, "char_limit": 20, "prompt": "write"}],
            "cover_letters": [letter] if include_letter else [], "followup_requests": []}


def actions(include_letter=True):
    return {"schema_version": 1, "run_id": RUN_ID,
            "screens": [{"job_id": 11, "decision": "pass", "reason": "Strong fit"}],
            "outreach_drafts": [{"job_id": 12, "content": "Useful first sentence. " + "x" * 700}],
            "request_results": [{"request_id": 13, "status": "ready", "content": "Fits. Too long for the configured limit."}],
            "cover_letter_drafts": [{"job_id": 14, "content": "A grounded letter."}] if include_letter else [],
            "notification": {"title": "Hourly run", "body": "0 new jobs"}}


class CloudConnectorTests(unittest.TestCase):
    def test_profile_requires_active_pdf(self):
        self.assertIn(PROFILE_TEXT.strip(), cc.profile_text(PROFILE))
        self.assertIn("ACTIVE REVIEWED PDF PROFILE VERSION: 2", cc.profile_text(PROFILE))
        self.assertEqual(cc.profile_text({"resume_text": PROFILE_TEXT}), "")
        self.assertEqual(cc.profile_text({**PROFILE, "status": "pending_review"}), "")

    def test_resume_filter_accepts_injected_profile(self):
        jobs = [{"title": "AI Engineer", "description": "Python RAG"}]
        kept, note = _resume_fit_filter(jobs, PROFILE_TEXT)
        self.assertEqual(len(kept), 1)
        self.assertIn("kept 1/1", note)

    def test_prepare_builds_only_explicitly_eligible_threshold_letters(self):
        jd = "Python FastAPI PostgreSQL machine learning production systems " * 12
        base_job = {"id": 14, "title": "AI Engineer", "company": "Acme", "description": jd,
                    "ats_score": 94, "profile_version": 2, "jd_version": 1,
                    "analysis_stale": False, "screen_decision": "pass",
                    "jd_hash": hashlib.sha256(jd.strip().encode()).hexdigest(),
                    "analysis_version": "explainable-match-v1",
                    "analysis_details": {"analysis_version": "explainable-match-v1",
                        "mandatory_eligibility": {"overall": "passed"},
                        "resume_jd_match": {"score": 94}}}
        context = {"schema_version": 1, "run_id": RUN_ID, "active_profile": PROFILE,
                   "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
                   "due_applications": [], "follow_up_history": [], "active_followup_requests": [],
                   "cover_letter_jobs": [base_job], "cover_letter_threshold": 90,
                   "completeness": {"follow_up_history": True, "active_followup_requests": True}}
        out = cc.prepare_items(context)
        self.assertEqual(len(out["cover_letters"]), 1)
        self.assertIn(PROFILE_TEXT.strip(), out["cover_letters"][0]["prompt"])
        self.assertIn(jd.strip(), out["cover_letters"][0]["prompt"])
        for score, eligibility in ((89, "passed"), (95, "review"), (95, "failed")):
            context["cover_letter_jobs"] = [{**base_job, "ats_score": score,
                "analysis_details": {"analysis_version": "explainable-match-v1",
                    "mandatory_eligibility": {"overall": eligibility},
                    "resume_jd_match": {"score": score}}}]
            self.assertEqual(cc.prepare_items(context)["cover_letters"], [])
        context["cover_letter_jobs"] = [{**base_job, "screen_decision": "review"}]
        self.assertEqual(cc.prepare_items(context)["cover_letters"], [])
        context["cover_letter_jobs"] = [{**base_job, "ats_score": 95}]
        with self.assertRaisesRegex(ValueError, "score does not match"):
            cc.prepare_items(context)

    def test_prepare_refuses_truncated_history(self):
        context = {"schema_version": 1, "run_id": RUN_ID, "active_profile": PROFILE,
                   "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
                   "due_applications": [], "follow_up_history": [], "active_followup_requests": [],
                   "cover_letter_jobs": [],
                   "completeness": {"follow_up_history": False, "active_followup_requests": True}}
        with self.assertRaisesRegex(ValueError, "not explicitly complete"):
            cc.prepare_items(context)

    def test_prepare_rescores_stale_job_against_exact_profile_and_jd(self):
        jd = "Python FastAPI PostgreSQL APIs in production " * 8
        context = {"schema_version": 1, "run_id": RUN_ID, "active_profile": PROFILE,
                   "rescore_jobs": [{"id": 18, "title": "AI Engineer", "location": "India",
                       "description": jd, "jd_version": 3,
                       "jd_hash": hashlib.sha256(jd.strip().encode()).hexdigest()}],
                   "screen_jobs": [], "outreach_jobs": [], "pending_requests": [],
                   "due_applications": [], "follow_up_history": [], "active_followup_requests": [],
                   "cover_letter_jobs": [],
                   "completeness": {"follow_up_history": True, "active_followup_requests": True}}
        out = cc.prepare_items(context)
        self.assertEqual(out["rescored_jobs"][0]["profile_version"], 2)
        self.assertEqual(out["rescored_jobs"][0]["jd_version"], 3)
        self.assertIn(out["rescored_jobs"][0]["analysis_details"]["document_readability"]["job_description"], {"partial", "readable"})
        context["rescore_jobs"][0]["jd_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "JD hash does not match"):
            cc.prepare_items(context)

    def test_validation_enforces_limits_membership_and_review(self):
        out = cc.validate_actions(prepared(), actions())
        self.assertLessEqual(len(out["request_results"][0]["content"]), 20)
        self.assertLessEqual(len(out["outreach_drafts"][0]["content"]), 600)
        self.assertEqual(out["cover_letter_drafts"][0]["resume_version"], 2)
        review = actions(); review["screens"][0]["decision"] = "review"
        self.assertEqual(cc.validate_actions(prepared(), review)["screens"][0]["decision"], "review")
        bad = actions(); bad["cover_letter_drafts"][0]["job_id"] = 999
        with self.assertRaisesRegex(ValueError, "outside the exported batch"):
            cc.validate_actions(prepared(), bad)

    def test_validation_rejects_duplicate_boolean_and_malformed_text(self):
        bad = actions(); bad["screens"].append(dict(bad["screens"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"): cc.validate_actions(prepared(), bad)
        bad = actions(); bad["screens"][0]["job_id"] = True
        with self.assertRaisesRegex(ValueError, "booleans"): cc.validate_actions(prepared(), bad)
        bad = actions(); bad["cover_letter_drafts"][0]["content"] = "bad\x00text"
        with self.assertRaisesRegex(ValueError, "control character"): cc.validate_actions(prepared(), bad)

    def test_validation_rejects_non_cold_dm_override(self):
        bad = actions(); bad["outreach_drafts"][0]["message_type"] = "screen"
        with self.assertRaisesRegex(ValueError, "must be cold_dm"): cc.validate_actions(prepared(), bad)

    def test_cover_letter_grounding_rejects_invented_numeric_and_skill_claims(self):
        bad = actions()
        bad["cover_letter_drafts"][0]["content"] = "I have 12 years of Kubernetes experience."
        with self.assertRaisesRegex(ValueError, "numeric claims absent"):
            cc.validate_actions(prepared(), bad)
        bad["cover_letter_drafts"][0]["content"] = "I have built Kubernetes platforms."
        with self.assertRaisesRegex(ValueError, "without active-profile evidence"):
            cc.validate_actions(prepared(), bad)
        good = actions()
        good["cover_letter_drafts"][0]["content"] = "I have built Python APIs for production systems."
        self.assertIn("Python APIs", cc.validate_actions(prepared(), good)["cover_letter_drafts"][0]["content"])

    def test_sql_is_retry_idempotent_and_run_scoped(self):
        first = cc.validate_actions(prepared(), actions())
        sql = cc.render_sql(first)
        self.assertIn("metadata->>'run_id'", sql)
        self.assertIn("ON CONFLICT (scraped_job_id, resume_version, jd_hash, generation_rules_version)", sql)
        self.assertIn("DO NOTHING", sql)
        self.assertIn("cover_letter_drafts", sql)
        marker = "O'Reilly; DROP TABLE scraped_jobs; --"
        value = actions(); value["cover_letter_drafts"][0]["content"] = marker
        self.assertNotIn(marker, cc.render_sql(cc.validate_actions(prepared(), value)))

    @patch("scraper.check_apply_type", return_value="EASY_APPLY")
    @patch("scraper.run_all_scrapers")
    def test_scrape_reuses_active_snapshot_and_provenance(self, run_all, _check):
        run_all.return_value = ([{"title": "AI Engineer", "company": "Acme", "location": "India",
            "source": "LinkedIn AI/ML", "url": "https://example.test/1",
            "description": "Python FastAPI machine learning role " * 30}], {"LinkedIn AI/ML": 1}, {})
        context = {"schema_version": 1, "run_id": RUN_ID, "existing_job_urls": [],
                   "active_profile": PROFILE, "last_email_subject": "Job Alert #8"}
        with patch.dict(os.environ, {"APPLY_CHECK_DELAY_SECONDS": "0"}): out = cc.scrape_plan(context)
        self.assertEqual(out["email_log"]["subject"], "Job Alert #9")
        self.assertEqual(out["jobs"][0]["profile_version"], 2)
        self.assertEqual(len(out["jobs"][0]["jd_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
