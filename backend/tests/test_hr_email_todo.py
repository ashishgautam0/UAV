import ast
import pathlib
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock


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


if __name__ == "__main__":
    unittest.main()