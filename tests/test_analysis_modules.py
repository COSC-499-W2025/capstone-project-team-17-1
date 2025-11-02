import sys
import unittest
from datetime import datetime

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.config import ConsentState  # noqa: E402
from capstone.language_detection import (  # noqa: E402
    classify_activity,
    detect_frameworks_from_package_json,
    detect_frameworks_from_python_requirements,
    detect_language,
)
from capstone.collaboration import analyze_git_logs  # noqa: E402
from capstone.collaboration_analysis import (  # noqa: E402
    build_collaboration_analysis,
    collect_git_contributions,
    format_analysis_as_csv,
)
from capstone.metrics import FileMetric, compute_metrics  # noqa: E402
from capstone.modes import resolve_mode  # noqa: E402
from capstone.skills import (  # noqa: E402
    SkillObservation,
    compute_skill_scores,
    drop_under_threshold,
)


class LanguageDetectionTests(unittest.TestCase):
    def test_detect_language_and_activity(self) -> None:
        self.assertEqual(detect_language("src/app.py"), "Python")
        self.assertEqual(detect_language("static/site.css"), "CSS")
        self.assertIsNone(detect_language("README"))

        self.assertEqual(classify_activity("docs/readme.md"), "documentation")
        self.assertEqual(classify_activity("assets/logo.png"), "asset")
        self.assertEqual(classify_activity("src/app.py"), "code")
        self.assertEqual(classify_activity("archive/data.bin"), "other")

    def test_detect_frameworks(self) -> None:
        package_json = '{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}'
        self.assertEqual(
            detect_frameworks_from_package_json(package_json), {"React", "Express"}
        )
        bad_json = "{not valid}"
        self.assertEqual(detect_frameworks_from_package_json(bad_json), set())

        requirements = ["Flask==2.3.0", "numpy==1.26.0"]
        self.assertEqual(detect_frameworks_from_python_requirements(requirements), {"Flask"})


class CollaborationTests(unittest.TestCase):
    def test_analyze_git_logs_classifies_contributors(self) -> None:
        logs = [
            "000 111 Alice Example <alice@example.com> 1700000000 +0000\tcommit",
            "111 222 Bob Example <bob@example.com> 1700000100 +0000\tcommit",
            "222 333 build bot <bot@ci> 1700000200 +0000\tcommit",
        ]
        summary = analyze_git_logs(logs)
        self.assertEqual(summary.classification, "collaborative")
        self.assertIn("Alice Example", summary.contributors)
        self.assertEqual(summary.primary_contributor, "Alice Example")

    def test_analyze_git_logs_handles_missing_matches(self) -> None:
        logs = ["Malformed line", "Another bad line"]
        summary = analyze_git_logs(logs)
        self.assertEqual(summary.classification, "unknown")
        self.assertEqual(summary.contributors, {})
        self.assertIsNone(summary.primary_contributor)

    def test_collect_git_contributions_filters_bots(self) -> None:
        entries = [
            {"author": "Alice", "email": "alice@example.com", "commits": 5},
            {"author": "CI Bot", "email": "ci@bot.com", "commits": 50, "is_bot": True},
        ]
        summary = collect_git_contributions(entries)
        self.assertEqual(summary["classification"], "individual")
        self.assertEqual(summary["human_contributors"], {"Alice": 5})
        self.assertIn("CI Bot", summary["bot_contributors"])

    def test_collect_git_contributions_honours_main_user(self) -> None:
        entries = [
            {"author": "Alice", "email": "alice@example.com", "commits": 3},
            {"author": "Bob", "email": "bob@example.com", "commits": 5},
            {"author": "Carol", "email": "carol@example.com", "commits": 2},
        ]
        summary = collect_git_contributions(entries, main_user="Bob")
        self.assertEqual(summary["classification"], "collaborative")
        self.assertEqual(summary["primary_contributor"], "Bob")


class MetricsTests(unittest.TestCase):
    def test_compute_metrics_summary(self) -> None:
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        files = [
            FileMetric(path="src/app.py", size=100, modified=base_time, activity="code"),
            FileMetric(path="docs/readme.md", size=50, modified=base_time.replace(day=2), activity="documentation"),
        ]
        summary = compute_metrics(files)
        self.assertEqual(summary.file_count, 2)
        self.assertEqual(summary.total_bytes, 150)
        self.assertEqual(summary.duration_days, 1)
        self.assertEqual(summary.activity_breakdown["code"], 1)
        self.assertEqual(summary.activity_breakdown["documentation"], 1)
        self.assertEqual(summary.active_days, 2)
        self.assertIn("2024-01", summary.timeline)


class ModeResolutionTests(unittest.TestCase):
    def _consent(self, granted: bool, decision: str) -> ConsentState:
        return ConsentState(granted=granted, decision=decision, timestamp="2024-01-01T00:00:00Z", source="test")

    def test_resolve_mode_defaults_to_local_for_unknown(self) -> None:
        result = resolve_mode("invalid", self._consent(True, "allow"))
        self.assertEqual(result.resolved, "local")

    def test_resolve_mode_external_not_supported(self) -> None:
        result = resolve_mode("external", self._consent(True, "allow"))
        self.assertEqual(result.resolved, "local")
        self.assertIn("not available", result.reason)

    def test_resolve_mode_auto_without_consent(self) -> None:
        result = resolve_mode("auto", self._consent(False, "deny"))
        self.assertEqual(result.resolved, "local")
        self.assertIn("Local analysis", result.reason)


class AdvancedCollaborationAnalysisTests(unittest.TestCase):
    def _sample_entries(self) -> list[dict]:
        return [
            {
                "author": "Alice",
                "email": "alice@example.com",
                "commits": 3,
                "reviews": 1,
                "coauthors": ["Carol"],
            },
            {
                "author": "Bob",
                "email": "bob@example.com",
                "commits": 2,
                "reviews": 3,
                "kind": "review",
                "coauthors": ["Alice"],
            },
        ]

    def test_build_collaboration_analysis_captures_reviews_and_exports(self) -> None:
        analysis = build_collaboration_analysis(self._sample_entries(), main_user="Alice")
        self.assertEqual(analysis.classification, "collaborative")
        self.assertEqual(analysis.primary_contributor, "Alice")
        self.assertIn("Alice", analysis.coauthors)
        self.assertIn("csv", analysis.exports)
        csv_output = analysis.exports["csv"]
        self.assertIn("Alice", csv_output)
        self.assertIn("Bob", csv_output)

    def test_build_collaboration_analysis_normalizes_scores_and_flags_shared(self) -> None:
        entries = [
            {
                "author": "SharedAccount",
                "email": "team+shared@example.com",
                "commits": 1,
                "shared": True,
            },
            {
                "author": "Dana",
                "email": "dana@example.com",
                "commits": 4,
                "lines": 100,
            },
        ]
        analysis = build_collaboration_analysis(entries, weights={"commit": 1.0, "lines": 0.01})
        self.assertAlmostEqual(sum(analysis.scores.values()), 1.0, places=4)
        self.assertIn("SharedAccount", analysis.flags["shared_accounts"])

    def test_build_collaboration_analysis_handles_empty(self) -> None:
        analysis = build_collaboration_analysis([])
        self.assertEqual(analysis.classification, "unknown")
        self.assertEqual(analysis.human_contributors, {})
        self.assertIn("csv", analysis.exports)

    def test_format_analysis_as_csv_includes_bots_when_requested(self) -> None:
        entries = [
            {"author": "Alice", "email": "alice@example.com", "commits": 1},
            {"author": "CI Bot", "email": "ci@bot.com", "commits": 1, "is_bot": True},
        ]
        analysis = build_collaboration_analysis(entries, include_bots=True)
        csv_output = format_analysis_as_csv(analysis, include_bots=True)
        self.assertIn("Alice", csv_output)
        self.assertIn("CI Bot", csv_output)


class SkillScoringTests(unittest.TestCase):
    def test_compute_dynamic_confidence_and_ordering(self) -> None:
        observations = [
            SkillObservation(skill="JavaScript", weight=60.0),
            SkillObservation(skill="SQL", weight=25.0),
            SkillObservation(skill="Python", weight=15.0),
        ]
        results = compute_skill_scores(observations, min_confidence=0.01)
        self.assertGreater(results[0].confidence, results[1].confidence)
        skills = [result.skill for result in results]
        self.assertEqual(skills, ["JavaScript", "SQL", "Python"])

    def test_drop_under_threshold_filters_noise(self) -> None:
        observations = [
            SkillObservation(skill="JavaScript", weight=5.0),
            SkillObservation(skill="Markdown", weight=0.1),
        ]
        scores = compute_skill_scores(observations, min_confidence=0.0)
        filtered = drop_under_threshold(scores, threshold=0.05)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].skill, "JavaScript")


if __name__ == "__main__":
    unittest.main()
