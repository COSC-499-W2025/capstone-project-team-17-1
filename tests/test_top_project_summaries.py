import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    # Make the project importable.
    sys.path.insert(0, str(SRC))

from capstone.project_ranking import ProjectRanking
from capstone.top_project_summaries import (
    AutoWriter,
    SummaryTemplate,
    create_summary_template,
    export_markdown,
    export_pdf_one_pager,
    export_readme_snippet,
    gather_evidence,
    generate_top_project_summaries,
)


SAMPLE_SNAPSHOT = {
    # Shared fixture like file_count.
    "file_summary": {
        "file_count": 8,
        "total_bytes": 4096,
        "active_days": 6,
        "timeline": {"2025-01": 3, "2025-02": 5},
    },
    "languages": {"Python": 5, "Markdown": 3},
    "frameworks": ["FastAPI", "PyTest"],
    "collaboration": {
        "classification": "collaborative",
        "contributors": {"Alice": 7, "Bob": 3},
    },
}


# tests:
class TopProjectSummariesTests(unittest.TestCase):
    def test_create_summary_template_includes_metadata(self) -> None:
        ranking = ProjectRanking(project_id="projA", score=0.91, breakdown={}, details={})
        template = create_summary_template("projA", SAMPLE_SNAPSHOT, ranking)
        self.assertEqual(template.title, "Top Project: projA")
        self.assertEqual(template.metadata["file_count"], 8)
        self.assertEqual(template.metadata["active_days"], 6)
        self.assertEqual(template.score_hint, 0.91)

    def test_gather_evidence_collects_snapshot_details(self) -> None:
        evidence = gather_evidence(SAMPLE_SNAPSHOT)
        kinds = {item.kind for item in evidence}
        self.assertIn("benchmark", kinds)
        self.assertTrue(any("collaboration" in item.reference for item in evidence))
        self.assertTrue(all(item.id is not None for item in evidence))

    def test_gather_evidence_includes_external_artifacts(self) -> None:
        snapshot = dict(SAMPLE_SNAPSHOT)
        snapshot["external_artifacts"] = {
            "pull_requests": [
                {
                    "number": 7,
                    "title": "Add reporting API",
                    "state": "merged",
                    "url": "https://example.invalid/pr/7",
                    "merged_at": "2024-01-02T10:00:00Z",
                    "user": "Alice",
                }
            ],
            "issues": [
                {
                    "number": 12,
                    "title": "Fix crash on export",
                    "state": "closed",
                    "url": "https://example.invalid/issues/12",
                    "user": "Bob",
                }
            ],
        }
        evidence = gather_evidence(snapshot)
        kinds = {item.kind for item in evidence}
        self.assertIn("pull_request", kinds)
        self.assertIn("issue", kinds)
        self.assertTrue(any(item.reference == "https://example.invalid/pr/7" for item in evidence))

    def test_gather_evidence_fetches_external_when_missing(self) -> None:
        snapshot = dict(SAMPLE_SNAPSHOT)
        snapshot["repository"] = {
            "provider": "github",
            "owner": "acme",
            "name": "demo",
            "url": "https://github.com/acme/demo",
        }
        fetched = {
            "pull_requests": [{"number": 5, "title": "LLM summary", "state": "open", "url": "https://example/pr/5"}],
            "issues": [],
        }
        with patch("capstone.top_project_summaries.fetch_snapshot_artifacts", return_value=fetched) as fetch_mock:
            evidence = gather_evidence(snapshot)
        fetch_mock.assert_called_once()
        self.assertTrue(any(item.kind == "pull_request" for item in evidence))

    def test_auto_writer_generates_summary_with_references(self) -> None:
        ranking = ProjectRanking(project_id="projA", score=0.88, breakdown={}, details={})
        template = SummaryTemplate(project_id="projA", title="Top Project: projA", sections=[], metadata={}, score_hint=0.88)
        evidence = gather_evidence(SAMPLE_SNAPSHOT)
        writer = AutoWriter()
        summary = writer.compose(template, evidence, SAMPLE_SNAPSHOT, ranking, rank_position=1)
        self.assertIn("[1]", summary.summary_text)
        self.assertGreater(len(summary.references), 0)
        self.assertGreater(summary.confidence["overall"], 0.0)

    def test_generate_top_project_summaries_orders_results(self) -> None:
        snapshots = {
            "projA": SAMPLE_SNAPSHOT,
            "projB": {
                "file_summary": {"file_count": 2, "total_bytes": 128, "active_days": 1, "timeline": {"2025-02": 2}},
                "languages": {"Python": 2},
                "frameworks": [],
                "collaboration": {"classification": "individual", "contributors": {"Casey": 2}},
            },
        }
        summaries = generate_top_project_summaries(snapshots, limit=2)
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["project_id"], "projA")
        self.assertTrue(summaries[0]["summary_text"])

    def test_exporters_produce_expected_formats(self) -> None:
        ranking = ProjectRanking(project_id="projA", score=0.95, breakdown={}, details={})
        template = create_summary_template("projA", SAMPLE_SNAPSHOT, ranking)
        evidence = gather_evidence(SAMPLE_SNAPSHOT)
        summary = AutoWriter().compose(template, evidence, SAMPLE_SNAPSHOT, ranking, rank_position=1)

        markdown = export_markdown(summary)
        self.assertTrue(markdown.startswith("# Top Project: projA"))
        pdf_bytes = export_pdf_one_pager(summary)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        snippet = export_readme_snippet(summary)
        self.assertIn("### Top Project: projA", snippet)
        self.assertIn("Evidence:", snippet)


if __name__ == "__main__":
    unittest.main()
