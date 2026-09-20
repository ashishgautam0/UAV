import ast
import io
import os
import pathlib
import sys
import types
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


ROOT = pathlib.Path(__file__).resolve().parents[1]


def function(path, name, env):
    node = next(
        item for item in ast.parse(path.read_text()).body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), env)
    return env[name]


class HrEmailTodoTests(unittest.TestCase):
    def test_mark_complete_and_reopen_persist_on_application(self):
        db = MagicMock()
        moment = datetime.fromisoformat("2026-09-20T12:00:00+05:30")
        update = function(
            ROOT / "modules/tracker.py",
            "set_hr_email_todo_completed",
            {"_get_client": lambda: db, "_user_now": lambda: moment},
        )

        self.assertEqual(update(42, True), moment.isoformat())
        db.table.assert_called_with("applications")
        db.table.return_value.update.assert_called_with({
            "hr_email_sent_at": moment.isoformat(),
        })
        db.table.return_value.update.return_value.eq.assert_called_with("id", 42)

        db.reset_mock()
        self.assertIsNone(update(42, False))
        db.table.return_value.update.assert_called_with({"hr_email_sent_at": None})

    def test_pending_query_excludes_terminal_records_and_maps_true_job_id(self):
        app_rows = [
            {"id": 1, "url": "https://jobs.test/one", "status": "Applied"},
            {"id": 2, "url": "https://jobs.test/two", "status": "Rejected"},
        ]

        class Query:
            def __init__(self, rows):
                self.rows = rows
                self.null_filter = None
            def select(self, *_): return self
            def is_(self, column, value):
                self.null_filter = (column, value)
                return self
            def order(self, *_args, **_kwargs): return self
            def in_(self, *_): return self
            def execute(self): return types.SimpleNamespace(data=self.rows)

        app_query = Query(app_rows)
        job_query = Query([{"id": 91, "url": "https://jobs.test/one"}])

        class DB:
            def table(self, name):
                return app_query if name == "applications" else job_query

        analytics = types.ModuleType("analytics")
        analytics.attach_tracker_job_ids = lambda apps, jobs: [
            {**row, "scraped_job_id": next(
                (job["id"] for job in jobs if job["url"] == row["url"]), None
            )}
            for row in apps
        ]
        fake_pd = types.SimpleNamespace(DataFrame=lambda rows=(): list(rows))
        load = function(
            ROOT / "modules/tracker.py",
            "get_hr_email_todos",
            {
                "_get_client": DB,
                "TERMINAL_STATUSES": ["Offer", "Rejected", "Ghosted", "Not Interested"],
                "pd": fake_pd,
            },
        )
        original = sys.modules.get("analytics")
        sys.modules["analytics"] = analytics
        try:
            self.assertEqual(load(), [{
                "id": 1,
                "url": "https://jobs.test/one",
                "status": "Applied",
                "scraped_job_id": 91,
            }])
        finally:
            if original is None:
                sys.modules.pop("analytics", None)
            else:
                sys.modules["analytics"] = original
        self.assertEqual(app_query.null_filter, ("hr_email_sent_at", "null"))

    def test_schema_backfills_only_old_rows_before_new_todos_begin(self):
        schema = (ROOT.parent / "supabase/schema.sql").read_text()
        migration = (ROOT.parent / "supabase/add_hr_email_todo.sql").read_text()
        self.assertIn("hr_email_sent_at      timestamptz", schema)
        self.assertIn("where hr_email_sent_at is null", migration)
        self.assertIn("if not exists (", migration)
        self.assertLess(migration.index("update public.applications"),
                        migration.index("create index if not exists"))

    def test_dashboard_detail_and_claude_flow_expose_the_todo(self):
        dashboard = (ROOT.parent / "frontend/src/app/(app)/dashboard/page.tsx").read_text()
        detail = (ROOT.parent / "frontend/src/app/(app)/jobs/[id]/page.tsx").read_text()
        readme = (ROOT.parent / "README.md").read_text()
        self.assertIn("Email Company HR", dashboard)
        self.assertIn("Mark emailed", dashboard)
        self.assertIn("Todo now — email Company HR", detail)
        self.assertIn("--type hr_email", readme)

    def test_hr_email_candidates_require_tracker_and_live_demo(self):
        apps = [
            {"url": "https://jobs.test/ready", "status": "Applied"},
            {"url": "https://jobs.test/no-demo", "status": "Applied"},
        ]
        jobs = [
            {"id": 10, "url": "https://jobs.test/ready", "title": "AI Engineer",
             "company": "Ready Co", "location": "", "description": "Role"},
            {"id": 20, "url": "https://jobs.test/no-demo", "title": "ML Engineer",
             "company": "No Demo Co", "location": "", "description": "Role"},
            {"id": 30, "url": "https://jobs.test/not-tracked", "title": "Other",
             "company": "Outside Co", "location": "", "description": "Role"},
        ]

        class Query:
            def __init__(self, rows): self.rows = rows
            def select(self, *_): return self
            def in_(self, column, values):
                self.rows = [row for row in self.rows if row.get(column) in values]
                return self
            def execute(self): return SimpleNamespace(data=self.rows)

        class DB:
            def table(self, name): return Query(list(apps if name == "applications" else jobs))

        tracker = types.ModuleType("tracker")
        tracker.TERMINAL_STATUSES = ["Offer", "Rejected", "Ghosted", "Not Interested"]
        tracker._get_client = DB
        tracker.get_job_message = lambda job_id, message_type: (
            {"content": "demo"} if message_type == "demo_html" and job_id == 10 else None
        )
        load = function(
            ROOT / "modules/pending_messages.py",
            "_tracked_jobs_missing",
            {"os": os},
        )
        with patch.dict(sys.modules, {"tracker": tracker}), \
             patch.dict(os.environ, {"PUBLIC_API_URL": "https://api.test/"}):
            candidates, tracked_total = load("hr_email", 10)

        self.assertEqual(tracked_total, 2)
        self.assertEqual([row["id"] for row in candidates], [10])
        self.assertEqual(candidates[0]["demo_url"], "https://api.test/api/demo/10")
        self.assertIn("latest PDF", candidates[0]["resume_attachment"])

    def test_hr_email_save_enforces_tracker_demo_link_resume_and_length(self):
        saved_content = {}
        tracker = types.ModuleType("tracker")
        tracker.is_scraped_job_tracked = lambda _job_id: True
        save = MagicMock(return_value=True)

        def get_message(job_id, message_type):
            if message_type == "demo_html":
                return {"content": "<html>demo</html>"}
            if message_type == "hr_email" and saved_content:
                return {"content": saved_content["content"]}
            return None

        def save_message(job_id, content, message_type):
            saved_content["content"] = content
            return save(job_id, content, message_type=message_type)

        command = function(
            ROOT / "modules/pending_messages.py",
            "cmd_save",
            {
                "get_job_message": get_message,
                "save_job_message": save_message,
                "os": os,
                "sys": sys,
            },
        )
        args = SimpleNamespace(job_id=10, type="hr_email", content=None)
        valid = (
            "To: careers@ready.test\nSubject: AI Engineer application\n\n"
            "Dear Hiring Team,\n\nI applied for the AI Engineer role. One verified "
            "project matches your needs, and I built this concise working demo: "
            "https://api.test/api/demo/10. My resume is attached for review.\n\n"
            "Best regards,\nSubidh Khanal"
        )

        cases = [
            valid.replace("https://api.test/api/demo/10", ""),
            valid.replace("My resume is attached for review.", ""),
            valid + " extra" * 151,
        ]
        with patch.dict(sys.modules, {"tracker": tracker}), \
             patch.dict(os.environ, {"PUBLIC_API_URL": "https://api.test"}):
            for content in cases:
                with self.subTest(content=content[-30:]), \
                     patch("sys.stdin", io.StringIO(content)), \
                     patch("sys.stderr", new_callable=io.StringIO):
                    self.assertEqual(command(args), 1)
            save.assert_not_called()

            with patch("sys.stdin", io.StringIO(valid)), \
                 patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(command(args), 0)
        save.assert_called_once()

        tracker.is_scraped_job_tracked = lambda _job_id: False
        saved_content.clear()
        save.reset_mock()
        with patch.dict(sys.modules, {"tracker": tracker}), \
             patch.dict(os.environ, {"PUBLIC_API_URL": "https://api.test"}), \
             patch("sys.stdin", io.StringIO(valid)), \
             patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(command(args), 1)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
