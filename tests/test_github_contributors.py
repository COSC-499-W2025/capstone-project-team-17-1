import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.github_contributors import (  # noqa: E402
    collect_contributor_stats,
    compute_score,
    get_contributor_rankings,
    parse_repo_url,
    weights_hash,
)
from capstone.storage import (  # noqa: E402
    close_db,
    fetch_latest_contributor_stats,
    open_db,
    store_contributor_stats,
)


class _FakeClient:
    def get_contributor_stats(self, owner: str, repo: str):
        return [
            {
                "author": {"login": "alice"},
                "total": 5,
                "weeks": [{"a": 10, "d": 2}, {"a": 3, "d": 1}],
            }
        ]

    def get_contributors(self, owner: str, repo: str):
        return [{"login": "bob", "contributions": 3}]

    def search_issues_count(self, query: str):
        if "assignee:alice" in query and "type:pr" in query:
            return 2
        if "assignee:alice" in query and "type:issue" in query:
            return 1
        if "reviewed-by:alice" in query:
            return 4
        if "assignee:bob" in query and "type:pr" in query:
            return 1
        if "assignee:bob" in query and "type:issue" in query:
            return 0
        if "reviewed-by:bob" in query:
            return 2
        return 0


class GitHubContributorTests(unittest.TestCase):
    def test_parse_repo_url(self) -> None:
        self.assertEqual(parse_repo_url("https://github.com/org/repo"), ("org", "repo"))
        self.assertEqual(parse_repo_url("git@github.com:org/repo.git"), ("org", "repo"))
        self.assertEqual(parse_repo_url("org/repo"), ("org", "repo"))

    def test_compute_score(self) -> None:
        score = compute_score(
            {
                "commits": 10,
                "line_changes": 20,
                "pull_requests": 1,
                "issues": 2,
                "reviews": 3,
            },
            weights={
                "commits": 0.3,
                "line_changes": 0.25,
                "pull_requests": 0.2,
                "issues": 0.15,
                "reviews": 0.1,
            },
        )
        expected = 10 * 0.3 + 20 * 0.25 + 1 * 0.2 + 2 * 0.15 + 3 * 0.1
        self.assertAlmostEqual(score, expected, places=6)

    def test_collect_contributor_stats(self) -> None:
        stats = collect_contributor_stats(
            "org",
            "repo",
            client=_FakeClient(),
            weights={
                "commits": 0.3,
                "line_changes": 0.25,
                "pull_requests": 0.2,
                "issues": 0.15,
                "reviews": 0.1,
            },
            max_contributors=10,
        )
        by_name = {row.contributor: row for row in stats}
        self.assertEqual(by_name["alice"].commits, 5)
        self.assertEqual(by_name["alice"].line_changes, 16)
        self.assertEqual(by_name["alice"].pull_requests, 2)
        self.assertEqual(by_name["alice"].issues, 1)
        self.assertEqual(by_name["alice"].reviews, 4)
        self.assertEqual(by_name["bob"].commits, 3)
        self.assertEqual(by_name["bob"].line_changes, 0)

    def test_rankings_refresh_when_weights_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                conn = open_db(Path(tmpdir))
                old_weights = {
                    "commits": 0.3,
                    "line_changes": 0.25,
                    "pull_requests": 0.2,
                    "issues": 0.15,
                    "reviews": 0.1,
                }
                old_score = compute_score(
                    {
                        "commits": 10,
                        "line_changes": 5,
                        "pull_requests": 2,
                        "issues": 1,
                        "reviews": 0,
                    },
                    weights=old_weights,
                )
                store_contributor_stats(
                    conn,
                    project_id="demo",
                    contributor="alice",
                    commits=10,
                    line_changes=5,
                    pull_requests=2,
                    issues=1,
                    reviews=0,
                    score=old_score,
                    weights_hash=weights_hash(old_weights),
                    source="github",
                )

                new_weights = {
                    "commits": 0.25,
                    "line_changes": 0.25,
                    "pull_requests": 0.25,
                    "issues": 0.15,
                    "reviews": 0.1,
                }
                rankings = get_contributor_rankings(conn, "demo", weights=new_weights)
                self.assertEqual(rankings[0]["contributor"], "alice")

                updated = fetch_latest_contributor_stats(conn, "demo")[0]
                self.assertEqual(updated["weights_hash"], weights_hash(new_weights))
                self.assertAlmostEqual(
                    updated["score"],
                    compute_score(
                        {
                            "commits": 10,
                            "line_changes": 5,
                            "pull_requests": 2,
                            "issues": 1,
                            "reviews": 0,
                        },
                        weights=new_weights,
                    ),
                    places=6,
                )
            finally:
                close_db()


if __name__ == "__main__":
    unittest.main()
