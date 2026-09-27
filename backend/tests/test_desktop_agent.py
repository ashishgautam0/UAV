import re
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from test_settings_profile import ROOT, function
import profile as profile_data


def stub_tracker(existing_urls=(), applied_urls=()):
    """Replace the data layer so router logic is tested without Supabase."""
    calls = {"scraped": [], "applied": [], "window": []}
    module = ModuleType("tracker")
    module.add_application = lambda **kw: calls["applied"].append(kw)
    module.save_scraped_job = lambda **kw: calls["scraped"].append(kw)
    module.find_application_by_url = lambda url: {"id": 1} if url in applied_urls else None
    module.get_existing_job_urls = lambda since_days=None: (
        calls["window"].append(since_days), set(existing_urls))[1]
    module.dedup_window_days = lambda: 14
    return module, calls


class SeenUrlsTests(unittest.TestCase):
    def endpoint(self, module):
        return function(ROOT / "app/routers/desktop_agent.py", "seen_urls", {
            "get_existing_job_urls": module.get_existing_job_urls,
            "dedup_window_days": module.dedup_window_days,
            "Query": lambda default, **kw: default,
        })

    def test_default_window_matches_the_scraper(self):
        module, calls = stub_tracker({"https://a/1", "https://b/2"})
        result = self.endpoint(module)(days=None)
        self.assertEqual(calls["window"], [14])
        self.assertEqual(result["window_days"], 14)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["urls"], ["https://a/1", "https://b/2"])

    def test_caller_may_widen_the_window(self):
        module, calls = stub_tracker()
        self.assertEqual(self.endpoint(module)(days=30)["window_days"], 30)
        self.assertEqual(calls["window"], [30])


class RecordJobTests(unittest.TestCase):
    def endpoint(self, module):
        return function(ROOT / "app/routers/desktop_agent.py", "record_job", {
            "add_application": module.add_application,
            "save_scraped_job": module.save_scraped_job,
            "find_application_by_url": module.find_application_by_url,
            "DesktopAgentJobRequest": SimpleNamespace,
        })

    def job(self, **overrides):
        return SimpleNamespace(**{
            "title": "ML Engineer", "company": "Acme AI", "location": "Bangalore",
            "url": "https://portal/job/1", "source": "LinkedIn", "description": "Builds models",
            "status": "applied", "job_type": "Job", "notes": "Easy Apply", **overrides,
        })

    def test_applied_job_reaches_both_the_job_list_and_the_tracker(self):
        module, calls = stub_tracker()
        result = self.endpoint(module)(self.job())
        self.assertEqual(result, {"saved": True, "applied": True, "duplicate": False})
        self.assertEqual(len(calls["scraped"]), 1)
        self.assertEqual(calls["scraped"][0]["source"], "LinkedIn")
        self.assertEqual(len(calls["applied"]), 1)
        self.assertEqual(calls["applied"][0]["role"], "ML Engineer")
        self.assertEqual(calls["applied"][0]["platform"], "LinkedIn")
        self.assertEqual(calls["applied"][0]["url"], "https://portal/job/1")

    def test_repeat_of_an_applied_job_adds_no_second_tracker_row(self):
        module, calls = stub_tracker(applied_urls={"https://portal/job/1"})
        result = self.endpoint(module)(self.job())
        self.assertEqual(result, {"saved": True, "applied": False, "duplicate": True})
        self.assertEqual(calls["applied"], [])
        # The posting is still refreshed so its JD and dedup entry stay current.
        self.assertEqual(len(calls["scraped"]), 1)

    def test_skipped_job_feeds_dedup_without_claiming_an_application(self):
        module, calls = stub_tracker()
        result = self.endpoint(module)(self.job(status="skipped", notes="Senior-level title"))
        self.assertEqual(result, {"saved": True, "applied": False, "duplicate": False})
        self.assertEqual(len(calls["scraped"]), 1)
        self.assertEqual(calls["applied"], [])


class DesktopPromptTests(unittest.TestCase):
    def setUp(self):
        self.prompt = profile_data.default_desktop_prompt()

    def test_default_is_editable_through_settings(self):
        self.assertIn("desktop_prompt_template", profile_data._APPLICATION_PROMPT_FIELDS)
        stored = {"scoring_weights": {"application_prompt": {"hr_email_template": "mine"}}}
        with patch.object(profile_data, "get_profile", return_value=stored), patch.object(
            profile_data, "upsert_profile", side_effect=lambda username, data: data
        ):
            saved = profile_data.save_application_prompt_settings(
                data={"desktop_prompt_template": "My desktop prompt"})
        self.assertEqual(saved["desktop_prompt_template"], "My desktop prompt")
        self.assertEqual(saved["hr_email_template"], "mine")

    def render(self, saved_template="", resume=None):
        """Call the endpoint with the data layer stubbed, as the CI lane has no DB."""
        module, _ = stub_tracker()
        with patch.dict(sys.modules, {"tracker": module}):
            endpoint = function(ROOT / "app/routers/profile.py", "read_desktop_prompt", {
                "_PROMPT_PLACEHOLDER": re.compile(r"{{([a-z_][a-z0-9_]*)}}"),
                "_DEFAULT_USERNAME": "subidh",
                "get_application_prompt_settings":
                    lambda username: {"desktop_prompt_template": saved_template},
                "_application_pdf_metadata": lambda: resume,
                "HTTPException": RuntimeError,
                "Request": SimpleNamespace,
            })
            request = SimpleNamespace(url_for=lambda name: f"https://api.test/{name}")
            return endpoint(request)

    def test_rendering_leaves_no_unresolved_placeholder(self):
        self.assertIn("{{seen_urls_url}}", self.prompt)
        self.assertIn("{{record_url}}", self.prompt)
        result = self.render(resume={"filename": "résumé.pdf", "sha256": "abc"})
        self.assertNotIn("{{", result["content"])
        self.assertEqual(result["unresolved_placeholders"], [])
        self.assertIn("https://api.test/desktop_agent_seen_urls", result["content"])
        self.assertIn("https://api.test/desktop_agent_record_job", result["content"])
        self.assertIn("résumé.pdf", result["content"])
        self.assertIn("14", result["content"])
        self.assertFalse(result["customized"])
        self.assertEqual(result["issues"], [])

    def test_saved_prompt_wins_and_bad_placeholders_are_reported(self):
        result = self.render(saved_template="Mine {{nonsense}}", resume={"filename": "r.pdf"})
        self.assertTrue(result["customized"])
        self.assertEqual(result["template"], "Mine {{nonsense}}")
        self.assertEqual(result["unresolved_placeholders"], ["nonsense"])
        self.assertIn("unresolved placeholders", result["issues"][0])

    def test_missing_resume_is_surfaced_not_hidden(self):
        result = self.render(resume=None)
        self.assertTrue(any("PDF" in issue for issue in result["issues"]))
        self.assertIn("Resume.pdf", result["content"])

    def test_prompt_covers_linkedin_dedup_tracker_and_no_time_cap(self):
        for portal in ("LINKEDIN", "NAUKRI", "INSTAHYRE", "CUTSHORT", "WELLFOUND"):
            self.assertIn(portal, self.prompt)
        for required in ("STEP 0 — LOAD ALREADY-SEEN JOBS", "skip list",
                         "STEP 2 — RECORD EVERY JOB THROUGH THE API",
                         "Maximum 10 applications per portal", "No overall time limit"):
            self.assertIn(required, self.prompt)
        self.assertNotIn("Maximum 2 hours", self.prompt)

    def test_prompt_fits_the_saved_field_limit(self):
        limit = function(ROOT / "app/routers/profile.py", "_settings_field_limit", {})
        self.assertLess(len(self.prompt), limit("desktop_prompt_template"))
        self.assertEqual(limit("hr_email_template"), 12_000)
        self.assertEqual(limit("notice_period"), 500)


if __name__ == "__main__":
    unittest.main()
