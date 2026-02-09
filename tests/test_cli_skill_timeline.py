import contextlib
import io
import unittest
from unittest.mock import Mock, patch

import main


class CLISkillTimelineTests(unittest.TestCase):
    def _mock_db_ctx(self):
        # minimal context manager to satisfy `with _open_app_db() as conn:`
        return contextlib.nullcontext(object())

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_single_selection_calls_builder_with_sorted_project(self, _consent, _grant_consent, _exit_app):
        snapshots = [
            {"project_id": "b_proj", "snapshot": {"project_name": "Bravo"}},
            {"project_id": "a_proj", "snapshot": {"project_name": "Alpha"}},
        ]

        builder_return = [{"skill": "python"}]

        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", return_value=snapshots), \
            patch("main._build_skills_timeline_rows", return_value=builder_return) as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted skills"):

            inputs = ["8", "2", "2", "13"]  # select project #2 (Bravo), then back, then exit
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO) as buf:
                try:
                    main.main()
                except SystemExit:
                    pass

        # alphabetical sorting should make Alpha index 1, Bravo index 2
        build_mock.assert_called_once()
        selected = build_mock.call_args[0][0]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].get("project_id"), "b_proj")

        output = buf.getvalue()
        self.assertIn("1. Alpha", output)
        self.assertIn("2. Bravo", output)
        self.assertIn("formatted skills", output)

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_cancel_selection_skips_builder(self, _consent, _grant_consent, _exit_app):
        snapshots = [
            {"project_id": "p1", "snapshot": {"project_name": "ProjectOne"}},
        ]

        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", return_value=snapshots), \
            patch("main._build_skills_timeline_rows") as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted skills"):

            inputs = ["8", "", "13"]  # enter option 8, cancel selection, then exit
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO):
                try:
                    main.main()
                except SystemExit:
                    pass

        build_mock.assert_not_called()

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_multi_selection_passes_multiple_snapshots(self, _consent, _grant_consent, _exit_app):
        snapshots = [
            {"project_id": "b_proj", "snapshot": {"project_name": "Bravo"}},
            {"project_id": "a_proj", "snapshot": {"project_name": "Alpha"}},
        ]
        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", return_value=snapshots), \
            patch("main._build_skills_timeline_rows", return_value=[]) as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted"):

            inputs = ["8", "1 2", "2", "13"]  # pick both, back to menu, exit
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    main.main()

        build_mock.assert_called_once()
        selected = build_mock.call_args[0][0]
        self.assertEqual({s.get("project_id") for s in selected}, {"a_proj", "b_proj"})

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_forced_choice_reenters_flow(self, _consent, _grant_consent, _exit_app):
        snapshots = [
            {"project_id": "p1", "snapshot": {"project_name": "One"}},
        ]
        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", side_effect=[snapshots, snapshots]), \
            patch("main._build_skills_timeline_rows", return_value=[]) as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted"):

            # First run select 1, then choose "view another" -> forced_choice triggers second run, then select 1 again, back, exit
            inputs = ["8", "1", "1", "1", "2", "13"]
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    main.main()

        self.assertEqual(build_mock.call_count, 2)

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_input_validation_messages_and_bounds(self, _consent, _grant_consent, _exit_app):
        snapshots = [
            {"project_id": "b_proj", "snapshot": {"project_name": "Bravo"}},
            {"project_id": "a_proj", "snapshot": {"project_name": "Alpha"}},
        ]
        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", return_value=snapshots), \
            patch("main._build_skills_timeline_rows", return_value=[]) as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted"):

            # invalid: non-numeric, out-of-range 5, then valid 1; back, exit
            inputs = ["8", "a b", "5", "1", "2", "13"]
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO) as buf:
                with self.assertRaises(SystemExit):
                    main.main()

        build_mock.assert_called_once()
        out = buf.getvalue()
        self.assertIn("Invalid input", out)
        self.assertIn("Indices must be in 1–2", out)
        # blank now cancels selection, so no empty-input warning expected

    @patch("main._exit_app", side_effect=SystemExit)
    @patch("main.grant_consent", return_value=True)
    @patch("main.ensure_or_prompt_consent", return_value="granted_existing")
    def test_no_projects_prints_notice(self, _consent, _grant_consent, _exit_app):
        with patch("main._open_app_db", return_value=self._mock_db_ctx()), \
            patch("main.fetch_latest_snapshots", return_value=[]), \
            patch("main._build_skills_timeline_rows") as build_mock, \
            patch("main._format_skills_timeline", return_value="formatted"):

            inputs = ["8", "13"]
            with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO) as buf:
                with self.assertRaises(SystemExit):
                    main.main()

        build_mock.assert_not_called()
        self.assertIn("No projects found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
