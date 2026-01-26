import unittest
from capstone.project_insight import build_project_insight_prompt

class ProjectInsightTests(unittest.TestCase):
    def test_prompt_includes_requesting_user_role(self):
        snapshot = {
            "collaboration": {"primary_contributor": "Alice"},
            "file_summary": {"active_days": 3},
            "languages": {"Python": 10},
            "frameworks": ["Flask"],
        }
        prompt = build_project_insight_prompt(snapshot, "What did I do?", user="Alice")
        self.assertIn("Requesting user's role", prompt)
        self.assertIn("primary_contributor", prompt)

        prompt2 = build_project_insight_prompt(snapshot, "What did I do?", user="Bob")
        self.assertIn("collaborator", prompt2)  # if you want this, add contributors in snapshot
