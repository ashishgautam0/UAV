import re
import unittest
from types import SimpleNamespace
from typing import Literal
from unittest.mock import patch

from test_settings_profile import ROOT, function, profile_data
from app.models.schemas import ApplicationPromptSettings, RenderedApplicationPrompt


class OutreachSettingsTests(unittest.TestCase):
    def test_partial_save_keeps_other_prompts_and_answers(self):
        stored = {"scoring_weights": {"skill": 12, "application_prompt": {
            "prompt_template": "Applications {{batch_jobs}}", "followup_template": "My follow-ups",
            "hr_email_template": "My initial email", "notice_period": "Two weeks",
        }}}
        with patch.object(profile_data, "get_profile", return_value=stored), patch.object(
            profile_data, "upsert_profile", side_effect=lambda username, data: data
        ) as save:
            result = profile_data.save_application_prompt_settings(data={"cold_dm_template": "Brief DM"})
        self.assertEqual(result["followup_template"], "My follow-ups")
        self.assertEqual(result["hr_email_template"], "My initial email")
        self.assertEqual(result["notice_period"], "Two weeks")
        self.assertEqual(result["cold_dm_template"], "Brief DM")
        self.assertEqual(save.call_args.args[1]["scoring_weights"]["skill"], 12)

    def test_older_clients_do_not_clear_new_prompt_fields(self):
        body = ApplicationPromptSettings(prompt_template="Old client updated applications")
        self.assertEqual(body.model_dump(exclude_unset=True), {"prompt_template": body.prompt_template})

    def test_template_lengths_and_unknown_fields_rejected(self):
        from pydantic import ValidationError
        for payload in ({"followup_template": "x" * 12001}, {"unknown_template": "no"}):
            with self.assertRaises(ValidationError):
                ApplicationPromptSettings(**payload)

    def renderer(self):
        return function(ROOT / "app/routers/profile.py", "_render_outreach_prompt",
                        {"_PROMPT_PLACEHOLDER": re.compile(r"{{([a-z_][a-z0-9_]*)}}")})

    def test_each_default_is_standalone_with_resolved_pdf_and_app(self):
        for kind, template in profile_data.OUTREACH_DEFAULTS.items():
            with self.subTest(kind=kind):
                prompt, unknown = self.renderer()(template, {"filename": "résumé.pdf", "sha256": "abc"},
                                                  "https://app/dashboard", "https://api/pdf", kind.removesuffix("_template"))
                self.assertFalse(unknown)
                self.assertIn("résumé.pdf", prompt)
                self.assertIn("https://app/dashboard", prompt)
                self.assertIn("explicit confirmation immediately before sending", prompt)
                self.assertNotIn("{{", prompt)
        self.assertNotIn("HR EMAIL —", profile_data.OUTREACH_DEFAULTS["followup_template"])
        self.assertIn("no dedicated cold-DM sent flag", profile_data.OUTREACH_DEFAULTS["cold_dm_template"])

    def test_custom_outreach_retains_send_guards_and_reports_unknown_placeholders(self):
        prompt, unknown = self.renderer()("My brief {{unsupported}}", {}, "https://app", "https://pdf")
        self.assertEqual(unknown, ["unsupported"])
        self.assertIn("My brief", prompt)
        self.assertIn("Check conversation/Sent history", prompt)

    def test_gmail_recipient_rules_apply_to_saved_email_templates_only(self):
        for kind in ("hr_email", "followup", "cold_dm"):
            prompt, _ = self.renderer()("Previously saved custom instructions", {}, "https://app", "https://pdf", kind)
            self.assertIn("Previously saved custom instructions", prompt)
            if kind == "cold_dm":
                self.assertNotIn("GMAIL AND HR RECIPIENT CHECKS", prompt)
            else:
                for requirement in ("Use my Gmail account", "actual PDF attachment", "visible From",
                                    "five relevant pages", "official job listing", "hiring entity",
                                    "Never construct firstname.lastname@", "Unverified is not the same",
                                    "Do not send test emails", "exact source URL", "explicit confirmation",
                                    "do not blindly Reply", "old and replacement recipients",
                                    "not delivery", "leave the todo pending"):
                    self.assertIn(requirement, prompt)

    def test_endpoint_passes_selected_workflow_to_renderer(self):
        seen = []
        def render(template, resume, page_url, resume_url, kind):
            seen.append(kind)
            return "prompt", []
        endpoint = function(ROOT / "app/routers/profile.py", "read_outreach_prompt", {
            "Request": object, "Literal": Literal, "RenderedApplicationPrompt": RenderedApplicationPrompt,
            "_clean_text": lambda value, maximum: value, "_DEFAULT_USERNAME": "fixture",
            "get_application_prompt_settings": lambda _: profile_data.OUTREACH_DEFAULTS,
            "_application_pdf_metadata": lambda: {"filename": "resume.pdf"}, "_render_outreach_prompt": render,
        })
        for kind in ("hr_email", "followup", "cold_dm"):
            endpoint(SimpleNamespace(url_for=lambda _: "https://api/pdf"), "https://app/dashboard", kind)
        self.assertEqual(seen, ["hr_email", "followup", "cold_dm"])

    def test_connection_note_rules_apply_to_old_custom_cold_dm_templates(self):
        prompt, unresolved = self.renderer()("My saved generic DM prompt", {}, "https://app", "https://pdf", "cold_dm")
        self.assertFalse(unresolved)
        for required in ("'Send it to'", "'Recruiters at [company]'", "'Hiring managers at [company]'",
                         "search links, not verified people", "current employment", "Connect → Add a note",
                         "not Gmail, InMail", "one-click Connect", "300 characters", "live composer limit",
                         "cannot attach a resume", "already connected", "If Pending", "canonical recipient",
                         "at most once", "acceptance pending", "not the overall", "stop invitation sending",
                         "no dedicated connection-invitation sent flag", "My saved generic DM prompt"):
            self.assertIn(required, prompt)
        for kind in ("hr_email", "followup"):
            other, _ = self.renderer()("Email template", {}, "https://app", "https://pdf", kind)
            self.assertNotIn("LINKEDIN COLD DM = CONNECTION REQUEST", other)

    def test_outreach_readiness_is_independent_of_today_todo_and_submission_authorization(self):
        for resume, expected in (({"filename": "active.pdf", "sha256": "abc"}, True), (None, False)):
            env = {"Request": object, "Literal": Literal, "RenderedApplicationPrompt": RenderedApplicationPrompt,
                   "_clean_text": lambda value, maximum: value, "_DEFAULT_USERNAME": "fixture",
                   "get_application_prompt_settings": lambda _: profile_data.OUTREACH_DEFAULTS,
                   "_application_pdf_metadata": lambda: resume, "_render_outreach_prompt": self.renderer()}
            endpoint = function(ROOT / "app/routers/profile.py", "read_outreach_prompt", env)
            for kind in ("followup", "cold_dm", "hr_email"):
                result = endpoint(SimpleNamespace(url_for=lambda _: "https://api/pdf"), "https://app/dashboard", kind)
                self.assertEqual(result.ready, expected)
                self.assertEqual(result.job_count, 0)


if __name__ == "__main__":
    unittest.main()
