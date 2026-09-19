import ast
import pathlib
import sys
import unittest
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from resume_profile import profile_text

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

if __name__ == "__main__":
    unittest.main()
