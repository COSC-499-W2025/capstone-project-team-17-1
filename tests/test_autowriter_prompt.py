import unittest

from capstone.top_project_summaries import AutoWriter, SummaryTemplate, EvidenceItem
from capstone.project_ranking import ProjectRanking


class TestAutoWriterPrompt(unittest.TestCase):

    def setUp(self):
        self.writer = AutoWriter(llm=None)

        self.template = SummaryTemplate(
            project_id="demo-project",
            title="Top Project: demo-project",
            sections=[],
            metadata={},
        )

        self.evidence = [
            EvidenceItem(
                id="E1",
                kind="benchmark",
                reference="analysis:file_count",
                detail="Processed 10 files",
                source="snapshot",
                weight=1.0,
            )
        ]

        self.snapshot = {
            "file_summary": {
                "first_modified": "2024-01-01",
                "last_modified": "2024-03-01",
                "active_days": 42,
            },
            "languages": {"Python": 10},
            "frameworks": [],
            "collaboration": {
                "primary_contributor": "alice",
                "contributors": {"alice": 8, "bob": 2},
            },
        }

        self.ranking = ProjectRanking(
            project_id="demo-project",
            score=0.87,
            breakdown={},
            details={},
        )

    def test_prompt_contains_required_sections(self):
        prompt = self.writer._build_prompt(
            template=self.template,
            evidence=self.evidence,
            snapshot=self.snapshot,
            ranking=self.ranking,
            rank_position=1,
        )

        # Ownership
        self.assertIn("Ownership:", prompt)
        self.assertIn("Primary contributor", prompt)

        # Timeline
        self.assertIn("Timeline:", prompt)
        self.assertIn("Active days", prompt)

        # Skills / Stack
        self.assertIn("Skills and Stack:", prompt)
        self.assertIn("Languages:", prompt)
        self.assertIn("Frameworks:", prompt)

        # Resume friendly constraints
        self.assertIn("resume ready bullet points", prompt)
        self.assertIn("Cite evidence using [n]", prompt)
        self.assertIn("Keep each bullet under 25 words", prompt)


if __name__ == "__main__":
    unittest.main()
