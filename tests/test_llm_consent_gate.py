import unittest
from unittest.mock import patch

from capstone.ai_insights import ask_project_question
from capstone.consent import ExternalPermissionDenied


class TestLLMConsentGate(unittest.TestCase):

    @patch("capstone.ai_insights.ensure_external_permission")
    @patch("capstone.ai_insights.fetch_latest_snapshot")
    @patch("capstone.ai_insights.rank_projects_from_snapshots")
    def test_llm_skipped_when_consent_denied(
        self,
        mock_rank,
        mock_fetch,
        mock_consent,
    ):
        mock_fetch.return_value = {
            "file_summary": {"active_days": 5},
            "languages": {"Python": 3},
            "frameworks": [],
            "collaboration": {"primary_contributor": "alice"},
        }
        mock_rank.return_value = []

        mock_consent.side_effect = ExternalPermissionDenied("blocked")

        result = ask_project_question(
            project_id="demo",
            question="What are the strengths?",
        )

        self.assertIn("AI-based analysis was skipped", result)

    @patch("capstone.ai_insights.ensure_external_permission")
    @patch("capstone.ai_insights.fetch_latest_snapshot")
    @patch("capstone.ai_insights.rank_projects_from_snapshots")
    @patch("capstone.ai_insights.LLMClient")
    def test_llm_used_when_consent_granted(
        self,
        mock_llm,
        mock_rank,
        mock_fetch,
        mock_consent,
    ):
        mock_fetch.return_value = {
            "file_summary": {"active_days": 5},
            "languages": {"Python": 3},
            "frameworks": [],
            "collaboration": {"primary_contributor": "alice"},
        }
        mock_rank.return_value = []
        mock_consent.return_value = None

        mock_llm.return_value.ask.return_value = "AI RESPONSE"

        result = ask_project_question(
            project_id="demo",
            question="What are the strengths?",
        )

        self.assertEqual(result, "AI RESPONSE")
        mock_llm.return_value.ask.assert_called_once()


if __name__ == "__main__":
    unittest.main()
