import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import main

JOB_DESC = """ Experience with Python, C++, SQL, Flask, cloud platforms. Strong understanding of data structures and algorithms."""

class TestJobDescMenu(unittest.TestCase):
    @patch("main.match_job_to_project")
    @patch("builtins.print")
    @patch("builtins.input")
    
    def test_paste_job_desc_compare_proj(self, mock_input, mock_print, mock_match):
        mock_input.side_effect = ["4", "1", JOB_DESC, "2", "demo_project", "0"]
        
        mock_match.return_value = MagicMock(
            project_id = "demo-project",
            job_skills = ["python", "sql"],
            matched_skills = [
                {"skill": "python", "category": "language", "confidence": "0.9"},
                {"skill": "sql", "category": "language", "confidence": "0.7"}
            ],
            missing_skills = ["aws"]
        )
        
        main.main()
        
        mock_match.assert_called_once()
        
        output = " ".join(
            str(c.args[0]) for c in mock_print.call_args_list if c.args
        ).lower()
        
        self.assertIn("relevant skills", output)
        self.assertIn("python", output)
        self.assertIn("sql", output)
        self.assertIn("aws", output)
        
    @patch("main.match_job_to_project")
    @patch("builtins.print")
    @patch("builtins.input")
    def test_paste_job_desc_rank_all_proj(self, mock_input, mock_print, mock_match):
        mock_input.side_effect = ["4", "1", JOB_DESC, "1", "0"]
        
        mock_match.return_value = MagicMock(
            project_id = "demo",
            job_skills = ["python"],
            matched_skills = [
                {"skill": "python", "confidence": "0.9"}],
            missing_skills = []
        )
        
        
        main.main()
        
        self.assertTrue(mock_match.called)
        
    @patch("main.match_job_to_project")
    @patch("builtins.print")
    @patch("builtins.input")
    def test_load_job_desc_from_file(self, mock_input, mock_print, mock_match, mock_read_text):
        mock_read_text.return_value = JOB_DESC
        mock_input.side_effect = ["4", "2", "job.txt", "2", "demo-project", "0"]
        
        mock_match.return_value = MagicMock(
            project_id = "demo-project",
            job_skills = ["python"],
            matched_skills = [{"skill": "python", "confidence": 0.9}],
            missing_skills = ["c++"]
        )
        
        main.main()
        
        mock_read_text.assert_called_once()
        mock_match.assert_called_once()
        
    @patch("builtins.print")
    @patch("builtins.input")
    def test_exit_job_description_menu(
        self,
        mock_input,
        mock_print,
    ):
        """User exits job description menu immediately"""

        mock_input.side_effect = [
            "4",  # Job Description menu
            "0",  # Exit
            "0",  # Exit main menu
        ]

        main.main()

        printed = " ".join(
            str(c.args[0]) for c in mock_print.call_args_list if c.args
        ).lower()

        self.assertIn("job description", printed)


if __name__ == "__main__":
    unittest.main()
        
        