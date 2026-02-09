import unittest

from capstone.project_insight import build_project_insight_prompt


class ProjectInsightEvidenceTests(unittest.TestCase):
    def test_prompt_includes_evidence_of_success_lines(self):
        snapshot = {
            "collaboration": {"primary_contributor": "Alice"},
            "file_summary": {"active_days": 3},
            "languages": {"Python": 10},
            "frameworks": [],
        }

        prompt = build_project_insight_prompt(
            snapshot=snapshot,
            question="What did I do?",
            user="Bob",
        )

        # Evidence section exists
        self.assertIn("Evidence:", prompt)

        # These should match the current gather_evidence() wording you showed earlier
        self.assertIn("Active development across 3 days", prompt)
        self.assertIn("Python leading (10 files)", prompt)
        self.assertNotIn("Frameworks detected: Flask", prompt)
