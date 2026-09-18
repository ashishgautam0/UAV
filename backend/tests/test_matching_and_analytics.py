import json
import sys
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
sys.path.insert(0, str(ROOT))

from analytics import attach_tracker_job_ids, platform_effectiveness, role_analysis, status_breakdown, weekly_trend
from jd_analyzer import _extract_degree_requirements, _extract_experience_requirement, full_analyze, quick_ats
from ranking import compute_application_priority
from resume_profile import extract_profile_facts, phrase_present, reviewed_experience_months
import tracker
from app.models.schemas import UserProfileRequest
from pydantic import ValidationError

FIXTURES = Path(__file__).parent / "fixtures"


def snapshot(text, version=1):
    extracted = extract_profile_facts(text, today=date(2026, 9, 18))
    return {"id": 1, "version": version, "status": "active", "source_kind": "pdf",
            "raw_text": text, "facts": extracted["facts"], "readability": extracted["readability"]}


class MatchingTests(unittest.TestCase):
    def test_legacy_text_resume_input_is_rejected(self):
        with self.assertRaises(ValidationError):
            UserProfileRequest.model_validate({"resume_text": "plain text is not an upload"})

    def test_boundary_matching_stops_substrings(self):
        self.assertFalse(phrase_present("MongoDB", "go"))
        self.assertFalse(phrase_present("object storage", "rag"))
        self.assertFalse(phrase_present("NoSQL", "sql"))
        self.assertTrue(phrase_present("Go and SQL", "go"))

    def test_benchmark_scores(self):
        cases = json.loads((FIXTURES / "matching_benchmark.json").read_text())
        for case in cases:
            with self.subTest(case=case["name"]):
                self.assertEqual(quick_ats(case["jd"], snapshot(case["resume"])), case["expected_score"])

    def test_experience_uses_union_of_real_dates(self):
        entries = [{"start": "2024-01", "end": "2024-12"}, {"start": "2024-06", "end": "2025-05"}]
        self.assertEqual(reviewed_experience_months(entries), 17)
        self.assertIsNone(reviewed_experience_months([]))
        reqs = _extract_experience_requirement("Minimum 3-5 years of experience required")
        self.assertEqual(reqs[0]["years"], 3)
        year_only = extract_profile_facts("Experience\nEngineer\n2024 - 2025", today=date(2026, 9, 18))["facts"]
        self.assertIsNone(year_only["total_experience_months"])
        self.assertEqual(year_only["experience"][0]["date_precision"], "year_only_requires_review")

    def test_degree_alternatives_take_minimum_and_unknown_is_review(self):
        req = _extract_degree_requirements("Bachelor's or Master's degree required")[0]
        self.assertEqual(req["level"], "bachelor")
        result = full_analyze("Engineer", "Bachelor's degree required. Python.", snapshot("Python developer"))
        self.assertEqual(result["mandatory_eligibility"]["overall"], "review")

    def test_empty_jd_is_unknown_not_perfect(self):
        result = full_analyze("Engineer", "", snapshot("Python FastAPI"))
        self.assertIsNone(result["resume_jd_match"]["score"])
        self.assertEqual(result["verdict"], "unknown")

    def test_priority_is_separate_and_mandatory_failure_blocks(self):
        job = {"analysis_details": {"mandatory_eligibility": {"status": "not_met"},
               "resume_jd_match": {"score": 99}}, "scraped_at": "2026-09-18T00:00:00Z", "verdict": "EASY_APPLY"}
        score, _ = compute_application_priority(job, job["analysis_details"])
        self.assertEqual(score, 0)


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((FIXTURES / "analytics_applications.json").read_text())

    def test_platform_metric_has_correct_denominator(self):
        values = {row["platform"]: row for row in platform_effectiveness(self.rows)}
        self.assertEqual(values["LinkedIn"], {"platform": "LinkedIn", "applications": 2, "responses": 1, "response_rate": 50.0})
        self.assertEqual(values["Referral"]["response_rate"], 50.0)

    def test_status_breakdown_is_lossless(self):
        counts = status_breakdown(self.rows)
        self.assertEqual(sum(counts.values()), len(self.rows))
        self.assertEqual(counts["Assignment Submitted"], 1)
        self.assertEqual(counts["Ghosted"], 1)

    def test_weekly_trend_uses_dates_and_types(self):
        trend = weekly_trend(self.rows)
        self.assertEqual([row["week"] for row in trend], ["2026-09-07", "2026-09-14"])
        self.assertEqual(trend[0]["total"], 2)
        self.assertEqual(trend[0]["Internship"], 1)

    def test_role_families_are_mutually_exclusive_and_evidenced(self):
        rows = role_analysis(self.rows)
        self.assertEqual(sum(row["applied"] for row in rows), len(self.rows))
        genai = next(row for row in rows if row["role_keyword"] == "Generative AI / LLM")
        self.assertIn("Generative AI Engineer", genai["example_roles"])

    def test_tracker_navigation_uses_exact_id_and_preserves_missing(self):
        apps = [
            {"id": 7, "url": "https://jobs/one"},
            {"id": 8, "url": "https://jobs/missing"},
            {"id": 9, "url": "https://jobs/one-more"},
        ]
        mapped = attach_tracker_job_ids(apps, [
            {"id": 42, "url": "https://jobs/one"},
            {"id": 84, "url": "https://jobs/one-more"},
        ])
        self.assertEqual(mapped[0]["scraped_job_id"], 42)
        self.assertIsNone(mapped[1]["scraped_job_id"])
        self.assertEqual(mapped[2]["scraped_job_id"], 84)

    def test_application_list_emits_persisted_detail_ids(self):
        application_rows = [
            {"id": 1, "url": "https://jobs/alpha", "date_applied": "2026-09-18"},
            {"id": 2, "url": "https://jobs/beta", "date_applied": "2026-09-17"},
            {"id": 3, "url": "https://jobs/manual", "date_applied": "2026-09-16"},
        ]
        scraped_rows = [
            {"id": 101, "url": "https://jobs/alpha"},
            {"id": 202, "url": "https://jobs/beta"},
        ]

        class Query:
            def __init__(self, table): self.table = table
            def select(self, *_): return self
            def order(self, *_args, **_kwargs): return self
            def in_(self, key, values):
                self.values = values
                return self
            def execute(self):
                rows = application_rows if self.table == "applications" else scraped_rows
                return type("Response", (), {"data": rows})()

        class DB:
            def table(self, name): return Query(name)

        with patch.object(tracker, "_get_client", return_value=DB()):
            rows = tracker.get_all_applications().to_dict("records")
        self.assertEqual(
            [(row["id"], row["scraped_job_id"]) for row in rows],
            [(1, 101), (2, 202), (3, None)],
        )

    def test_follow_up_date_persists_iso_value(self):
        calls = {}
        class Query:
            def update(self, payload): calls["payload"] = payload; return self
            def eq(self, key, value): calls["where"] = (key, value); return self
            def execute(self): return None
        class DB:
            def table(self, name): calls["table"] = name; return Query()
        with patch.object(tracker, "_get_client", return_value=DB()):
            tracker.snooze_follow_up(9, "2026-10-03")
        self.assertEqual(calls, {"table": "applications", "payload": {"follow_up_date": "2026-10-03"}, "where": ("id", 9)})
        with self.assertRaises(ValueError):
            tracker.snooze_follow_up(9, "03/10/2026")


if __name__ == "__main__":
    unittest.main()
