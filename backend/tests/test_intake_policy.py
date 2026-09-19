import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from intake_policy import excluded_employer, experience_exclusion, filter_jobs

class IntakePolicyTests(unittest.TestCase):
    def test_large_employer_aliases(self):
        for company in ["TCS", "Tata Consultancy Services Ltd.", "Infosys Limited",
                        "Amazon Development Centre (India) Pvt. Ltd.", "HCLTech",
                        "Microsoft India Private Limited", "HTC Global Services"]:
            with self.subTest(company=company):
                self.assertTrue(excluded_employer(company))

    def test_unknown_and_similar_companies_are_kept(self):
        for company in ["Global AI Startup", "VisaBuddy", "Amazonia AI", "TCS Labs Startup", "", None]:
            with self.subTest(company=company):
                self.assertFalse(excluded_employer(company))

    def test_required_experience(self):
        for text in ["2+ years of experience required", "1.5 years experience",
                     "Experience: 2-4 years", "18 months of relevant experience",
                     "More than one year of experience", ">1 year experience",
                     "Minimum two years of professional experience",
                     "Required qualifications:\n3 years experience",
                     "2 years experience required, Python preferred"]:
            with self.subTest(text=text):
                self.assertIsNotNone(experience_exclusion(text))

    def test_eligible_or_unknown_experience(self):
        for text in ["1+ years experience", "0-2 years of experience",
                     "1–3 years experience", "12 months experience", "Fresher",
                     "3 years experience preferred", "Up to 2 years experience",
                     "Company founded 10 years ago. Python required.",
                     "Preferred qualifications:\n3 years experience",
                     "", None]:
            with self.subTest(text=text):
                self.assertIsNone(experience_exclusion(text))

    def test_required_section_resets_preferred(self):
        self.assertIsNotNone(experience_exclusion(
            "Preferred qualifications:\n3 years experience\nRequired qualifications:\n2 years experience"))

    def test_filter_uses_employer_not_technologies(self):
        jobs = [{"company": "Small Startup", "description": "Experience with Amazon Web Services"},
                {"company": "TCS", "description": ""},
                {"company": "Small Startup", "description": "2 years experience"}]
        kept, removed = filter_jobs(jobs)
        self.assertEqual(kept, jobs[:1])
        self.assertEqual(len(removed), 2)

    def test_actual_scraper_aggregator(self):
        # Execute the real aggregator with offline source fixtures; no third-party
        # packages, network requests or production database are involved.
        source = (ROOT / "modules" / "scraper.py").read_text()
        node = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == "run_all_scrapers")
        fixture = lambda: [{"company": "Infosys", "description": ""},
                           {"company": "Small Startup", "description": "18 months experience"},
                           {"company": "Small Startup", "description": "1 year experience"}]
        import os
        from unittest.mock import patch
        env = {"os": os, **{name: fixture for name in
               ["scrape_indeed_india", "scrape_partner_ats", "scrape_gulf", "scrape_linkedin"]}}
        # No Amazon binding: including its dedicated source would fail this test.
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<aggregator>", "exec"), env)
        with patch.dict(os.environ, {}, clear=True):
            jobs, counts, errors = env["run_all_scrapers"]()
        self.assertEqual(len(jobs), 4)
        self.assertFalse(errors)
        self.assertTrue(all(j["description"] == "1 year experience" for j in jobs))

    def test_persistence_guard_before_database_access(self):
        source = (ROOT / "modules" / "tracker.py").read_text()
        node = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == "save_scraped_job")
        def fail():
            raise AssertionError("Excluded job reached database")
        env = {"_get_client": fail}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<persistence>", "exec"), env)
        env["save_scraped_job"]("AI Engineer", "TCS", "", "", "https://example.test")
        env["save_scraped_job"]("AI Engineer", "Startup", "", "", "https://example.test",
                                description="2 years experience")

if __name__ == "__main__":
    unittest.main()
