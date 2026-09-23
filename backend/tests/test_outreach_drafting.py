import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_settings_profile import ROOT, function
from message_generator import build_cold_dm_prompt, build_hr_email_prompt
from outreach_quality import validate_outreach_draft


class OutreachDraftingTests(unittest.TestCase):
    def test_connection_note_boundaries_and_malformed_outputs(self):
        self.assertIsNone(validate_outreach_draft("cold_dm", "x" * 300))
        for text in ("x" * 301, "😀" * 151, "VARIANT 1: Hello", "Subject: Hello",
                     "To: hr@example.test", "My resume is attached."):
            self.assertIsNotNone(validate_outreach_draft("cold_dm", text))
        self.assertIsNone(validate_outreach_draft("hr_email", "My resume is attached."))

    def test_builders_separate_purpose_and_preserve_facts(self):
        cold = build_cold_dm_prompt("Acme", "ML Engineer", "Python needed", profile_text="Coursework: Python")
        self.assertEqual(cold["char_limit"], 300)
        self.assertIn("ONE LinkedIn connection-request note", cold["prompt"])
        self.assertIn("Coursework: Python", cold["prompt"])
        self.assertNotIn("VARIANT 1", cold["prompt"])
        email = build_hr_email_prompt("Acme", "ML Engineer", "Python needed", "https://demo/1", "Coursework: Python")
        for text in ("70–110", "https://demo/1", "unknown — recipient verification required",
                     "Coursework: Python", "never turn coursework", "Do not send email"):
            self.assertIn(text, email["prompt"])

    def test_list_emits_exact_job_and_single_profile_snapshot(self):
        for kind in ("cold_dm", "hr_email"):
            profile = MagicMock(return_value="Verified Python coursework")
            command = function(ROOT / "modules/pending_messages.py", "cmd_list", {
                "_tracked_jobs_missing": lambda *_: ([{"id": 7, "company": "Acme", "title": "ML Engineer",
                    "description": "Exact JD", "demo_url": "https://demo/7"}], 1),
                "_profile_text": profile, "json": json, "sys": sys})
            with patch("sys.stdout", new_callable=io.StringIO) as out:
                command(SimpleNamespace(type=kind, limit=10))
                result = json.loads(out.getvalue())
            profile.assert_called_once()
            prompt = result["jobs"][0]["draft_spec"]["prompt"]
            self.assertIn("Exact JD", prompt)
            self.assertIn("Verified Python coursework", prompt)

    def test_direct_save_and_queue_reject_long_notes_without_writing(self):
        save = MagicMock()
        direct = function(ROOT / "modules/pending_messages.py", "cmd_save", {
            "sys": sys, "save_job_message": save})
        complete = MagicMock()
        queue = function(ROOT / "modules/pending_messages.py", "cmd_fulfil", {
            "sys": sys, "get_message_request": lambda _: {"message_type": "cold-dm", "params": {}},
            "_build_prompt": lambda *_: {"char_limit": 300}, "complete_message_request": complete})
        with patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(direct(SimpleNamespace(type="cold_dm", job_id=7, content="x" * 301)), 1)
            self.assertEqual(queue(SimpleNamespace(request_id=8, content="x" * 301)), 1)
        save.assert_not_called()
        complete.assert_not_called()

    def test_queue_keeps_valid_note_exactly(self):
        complete = MagicMock(return_value=True)
        queue = function(ROOT / "modules/pending_messages.py", "cmd_fulfil", {
            "sys": sys, "get_message_request": lambda _: {"message_type": "cold-dm", "params": {}},
            "_build_prompt": lambda *_: {"char_limit": 300}, "complete_message_request": complete})
        note = "Interested in Acme’s ML role. My Python coursework is relevant; I would be glad to connect."
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(queue(SimpleNamespace(request_id=8, content=note)), 0)
        complete.assert_called_once_with(8, note)
