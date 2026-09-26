import ast
import json
import pathlib
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from resume_profile import profile_text
import profile as profile_data

def function(path, name, env):
    node = next(n for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), env)
    return env[name]

class SettingsProfileTests(unittest.TestCase):
    def test_response_uses_same_context_as_backend(self):
        public = function(ROOT / "app/routers/profile.py", "_public_snapshot", {"profile_text": profile_text})
        snapshot = {"version": 2, "facts": {"skills": [{"name": "Python"}]},
                    "raw_text": "PDF source evidence", "corrections": {"private": "internal"}}
        result = public(snapshot)
        self.assertEqual(result["backend_text"], profile_text(snapshot))
        self.assertNotIn("raw_text", result)
        self.assertNotIn("corrections", result)
        self.assertIsNone(public(None))

    def test_corrected_experience_label_is_rendered(self):
        text = profile_text({"version": 1, "facts": {"experience": [{
            "role": "Updated Engineer", "company": "Updated Company",
            "label": "OLD EXTRACTED LABEL", "start": "2025-01", "end": "present"}]}})
        self.assertIn("Updated Engineer Updated Company", text)
        self.assertNotIn("OLD EXTRACTED LABEL", text)

    def activate(self, status):
        db = MagicMock()
        db.rpc.return_value.execute.return_value.data = [{"id": 1, "version": 2}]
        env = {"_get_client": lambda: db,
               "get_resume_profile": lambda *_: {"status": status, "version": 2},
               "_snapshot": lambda row: row}
        activate = function(ROOT / "modules/profile.py", "activate_resume_profile", env)
        result = activate(1, {"skills": [{"name": "Python"}]})
        self.assertEqual(result["version"], 2)
        return db

    def test_active_edits_invalidate_all_dependent_types_before_rpc(self):
        db = self.activate("active")
        tables = [call.args[0] for call in db.table.call_args_list]
        self.assertEqual(tables, ["scraped_jobs", "job_messages", "cover_letter_drafts"])
        calls = [str(call) for call in db.mock_calls]
        self.assertLess(next(i for i,c in enumerate(calls) if "table().update" in c),
                        next(i for i,c in enumerate(calls) if c.startswith("call.rpc(")))

    def test_pending_activation_uses_existing_rpc_invalidation(self):
        db = self.activate("pending_review")
        db.table.assert_not_called()
        db.rpc.assert_called_once()

    def test_application_prompt_settings_are_allowlisted(self):
        stored = {
            "scoring_weights": {
                "application_prompt": {
                    "notice_period": "One month",
                    "unsupported": "must not escape",
                },
            },
        }
        with patch.object(profile_data, "get_profile", return_value=stored):
            result = profile_data.get_application_prompt_settings()
        self.assertEqual(result["notice_period"], "One month")
        self.assertIn("{{batch_jobs}}", result["prompt_template"])
        self.assertNotIn("unsupported", result)
        self.assertEqual(result["current_location"], "")

    def test_saving_application_prompt_preserves_other_scoring_settings(self):
        existing = {"scoring_weights": {"skill": 44, "application_prompt": {"notice_period": "old"}}}
        captured = {}

        def save(username, data):
            captured.update(data)
            return {"username": username, **data}

        with patch.object(profile_data, "get_profile", return_value=existing), \
             patch.object(profile_data, "upsert_profile", side_effect=save):
            result = profile_data.save_application_prompt_settings(
                data={"notice_period": "Two weeks", "unknown": "ignored"}
            )
        self.assertEqual(captured["scoring_weights"]["skill"], 44)
        self.assertEqual(result["notice_period"], "Two weeks")
        self.assertNotIn("unknown", captured["scoring_weights"]["application_prompt"])

    def test_malformed_application_prompt_settings_are_treated_as_empty(self):
        with patch.object(profile_data, "get_profile", return_value={
            "scoring_weights": {"application_prompt": ["not", "a", "mapping"]},
        }):
            result = profile_data.get_application_prompt_settings()
        self.assertTrue(all(
            value == "" for key, value in result.items() if not key.endswith("template")
        ))
        self.assertIn("{{resume_url}}", result["prompt_template"])

    def test_ready_prompt_resolves_fixed_batch_resume_and_saved_answers(self):
        render = function(
            ROOT / "app/routers/profile.py",
            "_render_application_prompt",
            {
                "json": json,
                "_APPLICATION_ANSWER_LABELS": {
                    "submission_authorization": "Submission authorization",
                    "notice_period": "Notice period",
                },
                "_PROMPT_PLACEHOLDER": re.compile(r"{{([a-z_]+)}}"),
            },
        )
        settings = {
            "submission_authorization": "Submit after required confirmation.",
            "notice_period": "One month",
        }
        template = (
            "{{application_answers}}\n{{page_url}}\n{{resume_filename}}\n"
            "{{resume_url}}\n{{resume_sha256}}\n{{batch_jobs}}"
        )
        jobs = [{
            "id": 91,
            "title": "ML Engineer",
            "company": "O'Reilly भारत",
            "location": "Remote",
            "source": "Indeed",
            "url": "https://jobs.example/91",
            "screening_status": "pass",
            "screening_reason": "Mandatory criteria verified",
            "description": "must not bloat the browser prompt",
        }]
        prompt, unresolved = render(
            template,
            settings,
            jobs,
            {"filename": "latest.pdf", "sha256": "abc123"},
            "https://app.example/tonight",
            "https://api.example/api/profile/resume/pdf",
        )
        self.assertFalse(unresolved)
        self.assertIn("Start working through the fixed batch immediately", prompt)
        self.assertIn("Apply only when screening_status is pass", prompt)
        self.assertIn("Read and accept required application terms, privacy/data-processing consents", prompt)
        self.assertIn("including when a saved custom template says to pause", prompt)
        self.assertIn("Do not opt into optional marketing", prompt)
        self.assertIn("unsupported factual assertion", prompt)
        self.assertIn("attempt the normal on-page challenge using supported browser", prompt)
        self.assertIn("If it cannot be completed, request the user's help, leave", prompt)
        self.assertIn("Never bypass the challenge or use a third-party solver", prompt)
        self.assertIn("Pause for login or a missing truthful answer", prompt)
        self.assertIn("no longer accepting applications", prompt)
        self.assertIn("permanently not found", prompt)
        self.assertIn("match job ID and URL; swipe left to Remove", prompt)
        self.assertIn("Do not mark it Applied or delete the database record", prompt)
        self.assertIn("For a temporary page error, login, unsolved CAPTCHA, or uncertain availability, leave its card", prompt)
        self.assertIn("Submission authorization: Submit after required confirmation.", prompt)
        self.assertIn('"job_id": 91', prompt)
        self.assertIn("O'Reilly भारत", prompt)
        self.assertIn("https://api.example/api/profile/resume/pdf", prompt)
        self.assertNotIn("HR EMAIL —", prompt)
        self.assertNotIn("FOLLOW-UPS —", prompt)
        self.assertNotIn("click 'Mark emailed'", prompt)
        self.assertNotIn("must not bloat", prompt)
        for placeholder in ("application_answers", "page_url", "resume_filename",
                            "resume_url", "resume_sha256", "batch_jobs"):
            self.assertNotIn("{{" + placeholder + "}}", prompt)

    def test_ready_prompt_reports_unknown_placeholder(self):
        render = function(
            ROOT / "app/routers/profile.py",
            "_render_application_prompt",
            {
                "json": json,
                "_APPLICATION_ANSWER_LABELS": {},
                "_PROMPT_PLACEHOLDER": re.compile(r"{{([a-z_]+)}}"),
            },
        )
        _, unresolved = render(
            "Run {{unsupported_field}} for {{batch_jobs}}",
            {},
            [],
            None,
            "https://app.example/tonight",
            "https://api.example/api/profile/resume/pdf",
        )
        self.assertEqual(unresolved, ["unsupported_field"])

    def test_standalone_hr_workflow_retains_queue_and_send_guards(self):
        prompt = profile_data.OUTREACH_DEFAULTS["hr_email_template"]
        self.assertIn("Do not generate or send HR email before tracking", prompt)
        self.assertIn("HR email pending assets", prompt)
        self.assertIn("HR email blocked: mail access required", prompt)
        self.assertIn("Do not treat saved application", prompt)
        self.assertIn("If already completed, skip", prompt)
        self.assertIn("never guess a Tracker ID", prompt)
        self.assertIn("Use only its 'Email Company HR' todo section", prompt)
        self.assertIn("can include previously tracked jobs", prompt)
        self.assertIn("click that dashboard card", prompt)
        self.assertIn("Do not scan company details or every Tracker record", prompt)
        self.assertIn("report a queue error", prompt)
        self.assertIn("verify that todo is no longer pending", prompt)
        self.assertNotIn("For each eligible job in this fixed batch", prompt)
        self.assertNotIn("pay a fee, send email, or apply", prompt)

    def test_settings_exposes_only_ready_prompt_copy(self):
        page = (ROOT.parent / "frontend/src/app/(app)/settings/page.tsx").read_text()
        self.assertIn("Ready-to-paste Codex prompt", page)
        self.assertIn("disabled={!renderedPrompt?.ready || promptDirty", page)
        self.assertIn("Copy complete prompt for Codex", page)

    def test_followups_use_dashboard_and_separate_confirmed_history_logging(self):
        followup = profile_data.OUTREACH_DEFAULTS["followup_template"]
        for requirement in ("Dashboard's 'Follow-ups Due'", "Click each dashboard follow-up card",
                            "skip future dates", "defer the follow-up", "pending draft",
                            "existing conversation/channel", "actual latest Settings PDF attachment",
                            "confirmation immediately before Send", "never blindly resend",
                            "Record sent follow-up", "do not also change status",
                            "at most one follow-up per record", "Never fabricate history"):
            self.assertIn(requirement, followup)
        detail = (ROOT.parent / "frontend/src/app/(app)/jobs/[id]/page.tsx").read_text()
        self.assertIn('entity_id: application.id', detail)
        self.assertIn('message_content: sentFollowUp.trim()', detail)
        self.assertIn('event.follow_up_number >= followUpDraft!.follow_up_number!', detail)
        self.assertIn('setFollowUpRecordLocked(true)', detail)

if __name__ == "__main__":
    unittest.main()
