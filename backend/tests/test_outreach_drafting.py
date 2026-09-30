import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test_settings_profile import ROOT, function
from email_finder import extract_published_emails
from outreach_quality import draft_recipient, unsourced_recipient
from message_generator import build_cold_dm_prompt, build_hr_email_prompt
from outreach_quality import UNKNOWN_RECIPIENT
from outreach_quality import validate_outreach_draft, wrong_demo_links


class DemoLinkValidationTests(unittest.TestCase):
    """A draft reused across two jobs carries the first job's demo link, which
    would point the second employer at a demo built for someone else's role."""

    DEMO = "https://uav-6qe7.vercel.app/api/demo/"

    def test_the_job_s_own_demo_link_passes(self):
        note = f"Built a demo for the role: {self.DEMO}54144 — open to connecting."
        self.assertEqual(wrong_demo_links(note, 54144), [])
        self.assertIsNone(validate_outreach_draft("cold_dm", note, 54144))

    def test_another_job_s_demo_link_is_rejected(self):
        # The real slip: Lear Labs (54144) received Viraaj's draft and link.
        note = f"Built a demo for the role: {self.DEMO}54075 — open to connecting."
        self.assertEqual(wrong_demo_links(note, 54144), ["54075"])
        problem = validate_outreach_draft("cold_dm", note, 54144)
        self.assertIsNotNone(problem)
        self.assertIn("54075", problem)

    def test_hr_emails_are_checked_too(self):
        body = f"Here is a demo for the role: {self.DEMO}999"
        self.assertIsNotNone(validate_outreach_draft("hr_email", body, 54144))
        self.assertIsNone(validate_outreach_draft("hr_email", body, 999))

    def test_a_draft_with_no_demo_link_is_unaffected(self):
        self.assertEqual(wrong_demo_links("No link here.", 54144), [])
        self.assertIsNone(validate_outreach_draft("cold_dm", "No link here.", 54144))

    def test_string_and_int_job_ids_compare_the_same(self):
        note = f"{self.DEMO}54144"
        self.assertEqual(wrong_demo_links(note, "54144"), [])
        self.assertEqual(wrong_demo_links(note, 54144), [])

    def test_missing_job_id_skips_the_check_rather_than_failing(self):
        self.assertEqual(wrong_demo_links(f"{self.DEMO}1", None), [])
        self.assertIsNone(validate_outreach_draft("cold_dm", f"{self.DEMO}1"))

    def test_every_foreign_id_is_reported_once(self):
        note = f"{self.DEMO}1 and {self.DEMO}2 and {self.DEMO}1"
        self.assertEqual(wrong_demo_links(note, 3), ["1", "2"])


class SaveJobMessageDemoGuardTests(unittest.TestCase):
    """The check has to sit at the save choke point, not only in the CLI, or a
    subagent writing through another path can still store a mismatched link."""

    def saver(self, writes):
        db = MagicMock()
        db.table.return_value.upsert.return_value.execute.side_effect = (
            lambda: writes.append(True))
        return function(ROOT / "modules/tracker.py", "save_job_message", {
            "JOB_MESSAGE_TYPES": ("screen", "cold_dm", "hr_email", "resume_points", "demo_html"),
            "DEFAULT_MESSAGE_TYPE": "cold_dm",
            "_get_client": lambda: db,
            "datetime": __import__("datetime").datetime,
        })

    def test_a_foreign_demo_link_is_refused_before_any_write(self):
        writes = []
        saved = self.saver(writes)(
            54144, "demo: https://x/api/demo/54075", message_type="cold_dm",
            profile_version=3)
        self.assertFalse(saved)
        self.assertEqual(writes, [], "nothing may reach the database")

    def test_the_job_s_own_link_still_saves(self):
        writes = []
        saved = self.saver(writes)(
            54144, "demo: https://x/api/demo/54144", message_type="cold_dm",
            profile_version=3)
        self.assertTrue(saved)
        self.assertEqual(len(writes), 1)

    def test_a_long_cold_dm_still_saves_here(self):
        """Only the demo check moved to this layer; widening it would start
        rejecting drafts that save fine today."""
        writes = []
        saved = self.saver(writes)(54144, "x" * 400, message_type="cold_dm",
                                   profile_version=3)
        self.assertTrue(saved)


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

    def test_an_address_the_posting_publishes_is_offered_as_evidence(self):
        """81% of stored drafts had no recipient because the only route was an
        open-ended web search. An address the employer wrote into its own
        posting is evidence already — the posting is the official source."""
        email = build_hr_email_prompt(
            "Acme", "ML Engineer", "Mail your CV to careers@acme.co.in", "https://demo/1",
            "Coursework: Python", published_emails=["careers@acme.co.in"])
        self.assertIn("PUBLISHED IN THIS POSTING (evidence", email["prompt"])
        self.assertIn("careers@acme.co.in", email["prompt"])
        # With nothing published the agent is sent to the employer's own pages,
        # and the unknown marker still has to survive as the honest fallback.
        blank = build_hr_email_prompt("Acme", "ML Engineer", "No email here", "https://demo/1",
                                      "Coursework: Python")
        self.assertIn("none — research the employer's own pages", blank["prompt"])
        self.assertIn("unknown — recipient verification required", blank["prompt"])

    def test_harvesting_keeps_hiring_mailboxes_and_drops_the_rest(self):
        # The two real postings in the tracker that carry an address.
        self.assertEqual(
            extract_published_emails("Reach us at hello@operinlabs.com for a chat."),
            ["hello@operinlabs.com"])
        self.assertEqual(
            extract_published_emails("Send to TalentAcquisitionIndia@revantage.com"),
            ["talentacquisitionindia@revantage.com"])
        for text, reason in (
            ("noreply@acme.com", "automated mailbox"),
            ("support@acme.com", "not a hiring mailbox"),
            ("someone@gmail.com", "free mail, not the employer"),
            ("jobs@naukri.com", "the job board, not the employer"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(extract_published_emails(text), [])
        # Punctuation, casing and duplicates.
        self.assertEqual(extract_published_emails("(hr@a.com). Also HR@A.COM"), ["hr@a.com"])
        self.assertEqual(extract_published_emails(None), [])

    def test_a_recipient_without_a_source_on_record_is_rejected(self):
        """17 of 27 stored drafts had an address traceable to nothing, and one
        replaced its own cached address with hr@<tradingname>.in. Saving now
        requires the recipient to match evidence we hold."""
        body = "Subject: Application\n\nHello,\n\nBody text.\n\nSubidh Khanal"
        cached = ["info@rawats.com"]

        # The real failure: an evidenced address on record, a different one used.
        invented = validate_outreach_draft(
            "hr_email", f"To: hr@disruptive.in\n{body}", 7, evidenced_emails=cached)
        self.assertIn("hr@disruptive.in", invented)
        self.assertIn("no source on record", invented)

        # The cached address, and one the posting printed, both pass.
        for good in ("info@rawats.com", "careers@acme.co.in"):
            with self.subTest(recipient=good):
                self.assertIsNone(validate_outreach_draft(
                    "hr_email", f"To: {good}\n{body}", 7,
                    evidenced_emails=["info@rawats.com", "careers@acme.co.in"]))

        # Honestly declining to name one stays valid — that is the fallback.
        self.assertIsNone(validate_outreach_draft(
            "hr_email", f"To: {UNKNOWN_RECIPIENT}\n{body}", 7, evidenced_emails=[]))
        # Callers that pass no evidence list are unaffected, so cold DMs and
        # older call sites keep saving exactly as before.
        self.assertIsNone(validate_outreach_draft("hr_email", f"To: any@where.com\n{body}", 7))

    def test_recipient_parsing_survives_real_draft_shapes(self):
        self.assertEqual(draft_recipient("To:   Careers@ACME.com  \nSubject: x"),
                         "careers@acme.com")
        self.assertEqual(draft_recipient(f"To: {UNKNOWN_RECIPIENT}"), "")
        self.assertEqual(draft_recipient("no to line here"), "")
        # Case and surrounding whitespace must not defeat the match.
        self.assertEqual(unsourced_recipient("To: HR@Acme.com", ["hr@acme.com"]), "")
        self.assertEqual(unsourced_recipient("To: hr@acme.com", []), "hr@acme.com")

    def test_harvesting_imports_without_any_third_party_package(self):
        """This lane installs nothing. A module-level `import requests` in
        email_finder broke the whole file's collection in CI while passing
        locally, so the harvester must need only the standard library."""
        source = (ROOT / "modules/email_finder.py").read_text()
        top_level = [
            line for line in source.splitlines()
            if line.startswith(("import ", "from ")) and "__future__" not in line
        ]
        self.assertNotIn("import requests", top_level)
        for stdlib in ("import re", "import json"):
            self.assertIn(stdlib, top_level)
        # requests is still reachable where it is actually needed.
        self.assertIn("    import requests", source)

    def test_the_pattern_guesser_is_documented_as_unusable_here(self):
        """Port 25 is blocked on Vercel and in the routine container, so every
        candidate returns as an unverified guess. Nothing may read it as a
        verified recipient."""
        finder = (ROOT / "modules/email_finder.py").read_text()
        self.assertIn("NOT evidence", finder)
        self.assertIn("port 25 is blocked", finder)
        agent = (ROOT.parent / ".claude/agents/recruiter-email.md").read_text()
        self.assertIn("Do not use its output as a recipient", agent)
        # The ordered source list that replaced the open-ended search.
        for source in ("published_emails", "/careers", "/contact", "careers.",
                       "The ATS the posting hands off to"):
            with self.subTest(source=source):
                self.assertIn(source, agent)
        self.assertIn("careers@ or jobs@ either", agent)

    def test_list_emits_exact_job_and_single_profile_snapshot(self):
        for kind in ("cold_dm", "hr_email"):
            profile = MagicMock(return_value="Verified Python coursework")
            command = function(ROOT / "modules/pending_messages.py", "cmd_list", {
                "_tracked_jobs_missing": lambda *_: ([{"id": 7, "company": "Acme", "title": "ML Engineer",
                    "description": "Exact JD", "demo_url": "https://demo/7"}], 1),
                "_profile_text": profile, "_demo_url_for_job": lambda _: "",
                "_company_intel_text": lambda _: "", "json": json, "sys": sys,
                "_cached_hiring_email": lambda _: ""})
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

    def test_the_note_follows_up_on_the_application_in_a_fixed_shape(self):
        """The old notes opened with praise ("...stood out") and never said the
        user had applied. The note is the follow-up on an application."""
        demo = "https://uav-6qe7.vercel.app/api/demo/53891"
        spec = build_cold_dm_prompt("Docusign", "GenAI Engineer", "LLM gateway work",
                                    profile_text="Fine-tuned an LLM", demo_url=demo)["prompt"]
        for required in ('1. "Hi, I recently applied for the GenAI Engineer role at Docusign."',
                         f'3. "I built a short demo for this role: {demo}."',
                         '4. "Glad to connect."', "stood out", "caught my eye"):
            with self.subTest(required=required):
                self.assertIn(required, spec)
        self.assertNotIn("earn a connection, not an interview", spec.lower())
        bare = build_cold_dm_prompt("Acme", "ML Engineer", "JD", profile_text="Python")["prompt"]
        self.assertIn("No demo exists for this job", bare)
        self.assertNotIn("/api/demo/", bare.split("Example (for shape only", 1)[0])

    def test_a_note_that_praises_the_company_is_rejected(self):
        for opener in ("Your real-time voice agents stood out.",
                       "Docusign's gateway work caught my eye.",
                       "Impressive platform!"):
            with self.subTest(opener=opener):
                self.assertIn("praises the company",
                              validate_outreach_draft("cold_dm", f"{opener} Glad to connect."))
        self.assertIsNone(validate_outreach_draft(
            "cold_dm", "Hi, I recently applied for the ML Engineer role at Acme. Glad to connect."))

    def test_saving_requires_the_application_and_this_jobs_demo(self):
        save = MagicMock(return_value=True)
        demo = "https://uav-6qe7.vercel.app/api/demo/7"
        def command(demo_url):
            return function(ROOT / "modules/pending_messages.py", "cmd_save", {
                "sys": sys, "save_job_message": save, "_demo_url_for_job": lambda _: demo_url,
                "get_job_message": lambda *a, **kw: {"content": "saved"}})
        good = (f"Hi, I recently applied for the ML Engineer role at Acme. I built RAG systems "
                f"like the one in the posting. I built a short demo for this role: {demo}. "
                "Glad to connect.")
        with patch("sys.stderr", new_callable=io.StringIO), \
             patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(command(demo)(SimpleNamespace(type="cold_dm", job_id=7,
                             content=good.replace("I recently applied for", "About"))), 1)
            self.assertEqual(command(demo)(SimpleNamespace(type="cold_dm", job_id=7,
                             content=good.replace(f" I built a short demo for this role: {demo}.", ""))), 1)
            save.assert_not_called()
            self.assertEqual(command(demo)(SimpleNamespace(type="cold_dm", job_id=7, content=good)), 0)
            # No demo yet: the note simply has no link.
            no_demo = good.replace(f" I built a short demo for this role: {demo}.", "")
            self.assertEqual(command("")(SimpleNamespace(type="cold_dm", job_id=7, content=no_demo)), 0)
        self.assertEqual(save.call_count, 2)

    def test_queue_keeps_valid_note_exactly(self):
        complete = MagicMock(return_value=True)
        queue = function(ROOT / "modules/pending_messages.py", "cmd_fulfil", {
            "sys": sys, "get_message_request": lambda _: {"message_type": "cold-dm", "params": {}},
            "_build_prompt": lambda *_: {"char_limit": 300}, "complete_message_request": complete})
        note = "Interested in Acme’s ML role. My Python coursework is relevant; I would be glad to connect."
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(queue(SimpleNamespace(request_id=8, content=note)), 0)
        complete.assert_called_once_with(8, note)
