import ast
import pathlib
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
            value == "" for key, value in result.items() if key != "prompt_template"
        ))
        self.assertIn("{{resume_url}}", result["prompt_template"])

if __name__ == "__main__":
    unittest.main()
