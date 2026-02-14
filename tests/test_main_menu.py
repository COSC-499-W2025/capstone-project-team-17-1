# tests/test_main_menu.py
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Avoid importing the real capstone.cli (heavy imports)
dummy_cli = types.ModuleType("capstone.cli")
dummy_cli.main = lambda argv=None: 0
dummy_cli.prompt_project_metadata = lambda *args, **kwargs: {}
dummy_cli.pick_zip_file = lambda *args, **kwargs: ""
sys.modules["capstone.cli"] = dummy_cli

import main as app  # noqa: E402
# Reset dummy so other tests can import the real CLI module.
sys.modules.pop("capstone.cli", None)


def _entrypoint():
    fn = getattr(app, "app_main", None) or getattr(app, "main", None)
    if fn is None:
        raise RuntimeError("main.py must expose app_main() or main()")
    return fn


class _FakeCursor:
    def __init__(self):
        self.calls = []
        self._rows = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        sql_lower = sql.lower()
        if "select distinct contributor" in sql_lower:
            self._rows = getattr(self, "_user_rows", [])
        elif "from contributor_stats" in sql_lower and "contributor" in sql_lower:
            self._rows = getattr(self, "_project_rows", [])
        elif "from contributor_stats" in sql_lower:
            self._rows = getattr(self, "_user_rows", [])
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return list(self._rows)


class _FakeConn:
    def __init__(self):
        self.cursor_obj = _FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def execute(self, sql, params=()):
        return self.cursor_obj.execute(sql, params)

    def executescript(self, script):
        self.cursor_obj.calls.append((script, ()))
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def close(self):
        return None


class _ConnCM:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class MainMenuTests(unittest.TestCase):
    def run_menu(
        self,
        inputs,
        *,
        grant=True,
        rows=None,
        consent_status="granted_existing",
        user_rows=None,
        resume_users=None,
    ):
        out = io.StringIO()
        conn = _FakeConn()
        conn.cursor_obj._user_rows = [("alice",)]
        conn.cursor_obj._project_rows = [("p1",)]
        if user_rows is not None:
            conn.cursor_obj._user_rows = user_rows
        if user_rows is not None and rows:
            conn.cursor_obj._project_rows = [(rows[0]["project_id"],)]

        if rows is None:
            rows = []
        if resume_users is None:
            resume_users = [{"id": 1, "username": "alice", "project_count": 1, "email": None}]

        input_iter = iter(list(inputs))
        def _next_input(_prompt=""):
            try:
                return next(input_iter)
            except StopIteration:
                raise SystemExit

        with (
            patch.object(app, "grant_consent", return_value=grant),
            patch.object(app, "ensure_or_prompt_consent", return_value=consent_status),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "_open_app_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "_list_resume_users", return_value=resume_users),
            patch.object(app, "_list_user_project_ids", return_value={r[0] for r in conn.cursor_obj._project_rows}),
            patch.object(app, "_load_user_contribution_map", return_value={}),
            patch.object(
                app,
                "_ensure_user_profile_for_resume",
                return_value={
                    "full_name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "123",
                    "city": "Victoria",
                    "state_region": "BC",
                    "github_url": "https://github.com/alice",
                    "portfolio_url": "https://alice.dev",
                },
            ),
            patch.object(app, "_build_user_resume_preview", return_value={"sections": []}),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch("builtins.input", side_effect=_next_input),
            redirect_stdout(out),
        ):
            try:
                _entrypoint()()
            except SystemExit:
                pass

        return out.getvalue(), conn

    def test_exits_when_consent_denied(self):
        text, _ = self.run_menu(inputs=[], grant=False, consent_status="denied")
        self.assertIn("Consent is required", text)

    def test_no_projects(self):
        text, _ = self.run_menu(inputs=["3", "14"], rows=[])
        self.assertIn("No projects found", text)

    def test_lists_projects(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        text, _ = self.run_menu(inputs=["3", "2", "14"], rows=rows)

        # Accept either name key depending on your printing logic
        self.assertTrue(("Demo" in text) or ("p1" in text))

    def test_analyze_calls_store(self):
        rows = []
        out = io.StringIO()
        conn = _FakeConn()

        with (
            patch.object(app, "grant_consent", return_value=True),
            patch.object(app, "ensure_or_prompt_consent", return_value="granted_existing"),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "_open_app_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "SnapshotStore") as store_mock,
            patch.object(app, "ArchiveAnalyzerService") as svc_mock,
            patch.object(app.os.path, "isfile", return_value=True),
            patch.object(app, "_record_zip_upload", return_value=None),
            patch.object(app, "_store_subproject_summaries", return_value=None),
            patch("builtins.input", side_effect=["1", "n", "C:\\tmp\\demo.zip", "", "n", "n", "14"]),
            redirect_stdout(out),
        ):
            svc_instance = svc_mock.return_value
            svc_instance.validate_archive.return_value = ("C:\\tmp\\demo.zip", None, 0)
            svc_instance.analyze.return_value = {"project_id": "demo", "collaboration": {}}
            store_instance = store_mock.return_value
            try:
                _entrypoint()()
            except SystemExit:
                pass

        svc_mock.assert_called()
        store_instance.store_snapshot.assert_called()

    def test_summary_calls_rank_and_template(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        out = io.StringIO()
        conn = _FakeConn()
        conn.cursor_obj._user_rows = [("alice",)]
        conn.cursor_obj._project_rows = [("p1",)]

        with (
            patch.object(app, "grant_consent", return_value=True),
            patch.object(app, "ensure_or_prompt_consent", return_value="granted_existing"),
            patch.object(app, "open_db", return_value=_ConnCM(conn)),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "generate_top_project_summaries", return_value=[{"id": "p1"}]),
            patch.object(app, "export_markdown", return_value="SUMMARY") as export_mock,
            patch("builtins.input", side_effect=["5", "1", "1", "n", "3", "14"]),
            redirect_stdout(out),
        ):
            try:
                _entrypoint()()
            except SystemExit:
                pass

        export_mock.assert_called()
        self.assertIn("SUMMARY", out.getvalue())

    def test_portfolio_showcase_menu_flow(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        text, _ = self.run_menu(inputs=["5", "1", "2", "1", "3", "3", "14"], rows=rows, user_rows=[("alice",)])
        self.assertIn("Portfolio Showcase Preview", text)

    def test_resume_preview_menu_flow(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        text, _ = self.run_menu(inputs=["6", "1", "", "3", "14"], rows=rows)
        self.assertIn("Preview Options", text)

    def test_resume_auto_generate_skip_export(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        resume_preview = {"sections": [{"name": "summary", "items": [{"excerpt": "ok"}]}]}

        with (
            patch.object(app, "_build_user_resume_preview", return_value=resume_preview),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch("capstone.resume_pdf_builder.build_markdown_from_resume", return_value="MD"),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "6",  # resume
                    "1",  # user
                    "",   # all projects
                    "1",  # auto-generate
                    "4",  # skip export
                    "14",
                ],
                rows=rows,
            )

        self.assertIn("Resume Preview", text)

    def test_user_profile_menu_edit_updates_db(self):
        fields = [
            ("username", "alice"),
            ("email", "alice@example.com"),
            ("full_name", ""),
            ("phone_number", ""),
            ("city", ""),
            ("state_region", ""),
            ("github_url", "https://github.com/alice"),
            ("portfolio_url", ""),
        ]

        with (
            patch.object(app, "_load_user_profile_fields_for_edit", return_value=fields),
            patch.object(app, "_update_user_profile_field") as update_mock,
        ):
            text, _ = self.run_menu(
                inputs=[
                    "13",  # manage user profile
                    "1",   # select user
                    "1",   # edit
                    "3",   # full_name
                    "Alice Doe",
                    "2",   # back
                    "14",  # exit
                ],
                rows=[],
            )

        update_mock.assert_called_once()
        kwargs = update_mock.call_args.kwargs
        self.assertEqual(kwargs.get("column_name"), "full_name")
        self.assertEqual(kwargs.get("value"), "Alice Doe")
        self.assertIn("Saved successfully.", text)

    def test_user_profile_menu_edit_blank_cancels_update(self):
        fields = [
            ("username", "alice"),
            ("email", "alice@example.com"),
            ("full_name", ""),
            ("phone_number", ""),
            ("city", ""),
            ("state_region", ""),
            ("github_url", "https://github.com/alice"),
            ("portfolio_url", ""),
        ]

        with (
            patch.object(app, "_load_user_profile_fields_for_edit", return_value=fields),
            patch.object(app, "_update_user_profile_field") as update_mock,
        ):
            text, _ = self.run_menu(
                inputs=[
                    "13",  # manage user profile
                    "1",   # select user
                    "1",   # edit
                    "",    # cancel field edit
                    "2",   # back
                    "14",  # exit
                ],
                rows=[],
            )

        update_mock.assert_not_called()
        self.assertIn("User Profile Details", text)

    def test_resume_customize_summary_add(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        entry = types.SimpleNamespace(
            id="e1",
            section="projects",
            title="Demo",
            summary="",
            body="",
            status="active",
            metadata={},
            project_ids=["p1"],
            skills=[],
        )

        def _update_resume_entry(_conn, **kwargs):
            if "summary" in kwargs and kwargs.get("_summary_provided"):
                entry.summary = kwargs.get("summary")
            return entry

        preview = {
            "sections": [
                {
                    "name": "projects",
                    "items": [
                        {
                            "id": "e1",
                            "section": "projects",
                            "title": "Demo",
                            "excerpt": "",
                            "entrySummary": "",
                            "entryBody": "",
                            "status": "active",
                            "projectIds": ["p1"],
                            "skills": [],
                        }
                    ],
                }
            ],
            "projectContext": {},
            "warnings": [],
        }

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "generate_resume_project_descriptions", return_value=None),
            patch.object(app, "query_resume_entries", return_value=types.SimpleNamespace(entries=[entry], warnings=[], missing_sections=[], schema_state=None)),
            patch.object(app, "build_resume_preview", return_value=preview),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch.object(app, "get_resume_entry", return_value=entry),
            patch.object(app, "update_resume_entry", side_effect=_update_resume_entry),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "6",  # resume preview
                    "1",  # pick user
                    "1",  # select project
                    "2",  # customize
                    "1",  # entry 1
                    "1",  # summary
                    "1",  # add
                    "Hello summary",  # text
                    "3",  # back from summary
                    "8",  # back from edit entry
                    "",   # cancel entry selection
                    "2",  # back to main menu
                    "14", # exit
                ],
                rows=rows,
            )

        self.assertIn("Saved successfully.", text)

    def test_resume_customize_skills_add(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        entry = types.SimpleNamespace(
            id="e1",
            section="projects",
            title="Demo",
            summary="",
            body="",
            status="active",
            metadata={},
            project_ids=["p1"],
            skills=[],
        )

        preview = {
            "sections": [
                {
                    "name": "projects",
                    "items": [
                        {
                            "id": "e1",
                            "section": "projects",
                            "title": "Demo",
                            "excerpt": "",
                            "entrySummary": "",
                            "entryBody": "",
                            "status": "active",
                            "projectIds": ["p1"],
                            "skills": [],
                        }
                    ],
                }
            ],
            "projectContext": {},
            "warnings": [],
        }

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "generate_resume_project_descriptions", return_value=None),
            patch.object(app, "query_resume_entries", return_value=types.SimpleNamespace(entries=[entry], warnings=[], missing_sections=[], schema_state=None)),
            patch.object(app, "build_resume_preview", return_value=preview),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch.object(app, "get_resume_entry", return_value=entry),
            patch.object(app, "update_resume_entry", return_value=entry),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "6",  # resume preview
                    "1",  # user
                    "1",  # project
                    "2",  # customize
                    "1",  # entry
                    "3",  # skills
                    "1",  # add
                    "Python",
                    "3",  # back from skills
                    "8",
                    "",
                    "2",
                    "14",
                ],
                rows=rows,
            )

        self.assertIn("Saved successfully.", text)

    def test_portfolio_showcase_customize_highlights(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        showcase_summary = (
            "# Top Project: Demo\\n\\n"
            "Top Project: Demo ranks #1 with a portfolio score of 0.5.\\n\\n"
            "## Highlights\\n"
            "- Existing highlight\\n\\n"
            "## References\\n"
            "- [1] Ref\\n"
        )

        def _fake_get_desc(_conn, project_id, variant_name=None, **_kwargs):
            return types.SimpleNamespace(summary=showcase_summary)

        def _fake_upsert(_conn, **kwargs):
            return types.SimpleNamespace(summary=kwargs.get("summary"))

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "get_resume_project_description", side_effect=_fake_get_desc),
            patch.object(app, "upsert_resume_project_description", side_effect=_fake_upsert),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "5",  # portfolio options
                    "1",  # user select
                    "2",  # showcase
                    "1",  # select project
                    "1",  # customize
                    "2",  # edit highlights
                    "1",  # add
                    "New highlight",
                    "5",  # back to showcase options
                    "3",  # back to portfolio menu
                    "14",
                ],
                rows=rows,
                user_rows=[("alice",)],
            )

        self.assertIn("Highlights updated successfully.", text)

    def test_portfolio_showcase_customize_references_delete(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        showcase_summary = (
            "# Top Project: Demo\n\n"
            "Top Project: Demo ranks #1 with a portfolio score of 0.5.\n\n"
            "## Highlights\n"
            "- Existing highlight\n\n"
            "## References\n"
            "- [1] Ref A\n"
            "- [2] Ref B\n"
        )

        def _fake_get_desc(_conn, project_id, variant_name=None, **_kwargs):
            return types.SimpleNamespace(summary=showcase_summary)

        def _fake_upsert(_conn, **kwargs):
            return types.SimpleNamespace(summary=kwargs.get("summary"))

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "get_resume_project_description", side_effect=_fake_get_desc),
            patch.object(app, "upsert_resume_project_description", side_effect=_fake_upsert),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "5", "1", "2", "1",
                    "1",  # customize
                    "3",  # edit references
                    "2",  # delete
                    "1",  # delete all
                    "5",  # back to showcase options
                    "3", "14",
                ],
                rows=rows,
                user_rows=[("alice",)],
            )

        self.assertIn("References updated successfully.", text)

    def test_portfolio_showcase_edit_full_markdown(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        def _fake_upsert(_conn, **kwargs):
            return types.SimpleNamespace(summary=kwargs.get("summary"))

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "get_resume_project_description", return_value=None),
            patch.object(app, "upsert_resume_project_description", side_effect=_fake_upsert),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "5", "1", "2", "1",
                    "1",  # customize
                    "4",  # edit full markdown
                    "FULL MARKDOWN",
                    "5",  # back to showcase options
                    "3", "14",
                ],
                rows=rows,
                user_rows=[("alice",)],
            )

        self.assertIn("Showcase content updated successfully.", text)

    def test_resume_customize_linked_projects_add(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        entry = types.SimpleNamespace(
            id="e1",
            section="projects",
            title="Demo",
            summary="",
            body="",
            status="active",
            metadata={},
            project_ids=[],
            skills=[],
        )

        preview = {
            "sections": [
                {
                    "name": "projects",
                    "items": [
                        {
                            "id": "e1",
                            "section": "projects",
                            "title": "Demo",
                            "excerpt": "",
                            "entrySummary": "",
                            "entryBody": "",
                            "status": "active",
                            "projectIds": [],
                            "skills": [],
                        }
                    ],
                }
            ],
            "projectContext": {},
            "warnings": [],
        }

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "generate_resume_project_descriptions", return_value=None),
            patch.object(app, "query_resume_entries", return_value=types.SimpleNamespace(entries=[entry], warnings=[], missing_sections=[], schema_state=None)),
            patch.object(app, "build_resume_preview", return_value=preview),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch.object(app, "get_resume_entry", return_value=entry),
            patch.object(app, "update_resume_entry", return_value=entry),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "6", "1", "1", "2",  # resume, user, project, customize
                    "1",  # entry
                    "4",  # linked projects
                    "1",  # add
                    "1",  # select project
                    "3",  # back
                    "8", "", "2", "14",
                ],
                rows=rows,
            )

        self.assertIn("Saved successfully.", text)

    def test_resume_customize_metadata_add(self):
        rows = [
            {
                "id": 1,
                "project_id": "p1",
                "snapshot": {"project_id": "p1", "project_name": "Demo"},
                "created_at": "2026-01-11T00:00:00Z",
            }
        ]

        entry = types.SimpleNamespace(
            id="e1",
            section="projects",
            title="Demo",
            summary="",
            body="",
            status="active",
            metadata={},
            project_ids=["p1"],
            skills=[],
        )

        preview = {
            "sections": [
                {
                    "name": "projects",
                    "items": [
                        {
                            "id": "e1",
                            "section": "projects",
                            "title": "Demo",
                            "excerpt": "",
                            "entrySummary": "",
                            "entryBody": "",
                            "status": "active",
                            "projectIds": ["p1"],
                            "skills": [],
                        }
                    ],
                }
            ],
            "projectContext": {},
            "warnings": [],
        }

        with (
            patch.object(app, "fetch_latest_snapshots", return_value=rows),
            patch.object(app, "generate_resume_project_descriptions", return_value=None),
            patch.object(app, "query_resume_entries", return_value=types.SimpleNamespace(entries=[entry], warnings=[], missing_sections=[], schema_state=None)),
            patch.object(app, "build_resume_preview", return_value=preview),
            patch.object(app, "_format_resume_preview", return_value="PREVIEW"),
            patch.object(app, "get_resume_entry", return_value=entry),
            patch.object(app, "update_resume_entry", return_value=entry),
        ):
            text, _ = self.run_menu(
                inputs=[
                    "6", "1", "1", "2",  # resume, user, project, customize
                    "1",  # entry
                    "7",  # metadata
                    "1",  # add
                    "2026-01", "2026-02",
                    "3",  # back
                    "8", "", "2", "14",
                ],
                rows=rows,
            )

        self.assertIn("Saved successfully.", text)

if __name__ == "__main__":
    unittest.main()
