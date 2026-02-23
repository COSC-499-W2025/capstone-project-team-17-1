import sys
import unittest
from pathlib import Path

# Ensure src is importable when running tests directly
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.code_bundle import BundledFile
from capstone.deep_review_prompt import build_deep_review_prompt


class TestDeepReviewPrompt(unittest.TestCase):
    def test_prompt_includes_snapshot_context_question_and_files(self):
        snapshot = {
            "file_summary": {"file_count": 42},
            "languages": {"Python": 1234, "JavaScript": 567},
            "frameworks": ["FastAPI", "React"],
            "collaboration": {"contributors": 3},
        }

        files = [
            BundledFile(path="src/a.py", text="print('x')\n", truncated=False),
            BundledFile(path="src/b.js", text="console.log('y')\n", truncated=True),
        ]

        q = "Is there a bug and how can I improve this"

        prompt = build_deep_review_prompt(snapshot, q, files)

        self.assertIn("Project context derived from metadata.", prompt)
        self.assertIn("File count: 42", prompt)
        self.assertIn("Frameworks: ['FastAPI', 'React']", prompt)
        self.assertIn("User question.", prompt)
        self.assertIn(q, prompt)

        self.assertIn("FILE: src/a.py", prompt)
        self.assertIn("TRUNCATED: False", prompt)
        self.assertIn("BEGIN", prompt)
        self.assertIn("print('x')", prompt)
        self.assertIn("END", prompt)

        self.assertIn("FILE: src/b.js", prompt)
        self.assertIn("TRUNCATED: True", prompt)
        self.assertIn("console.log('y')", prompt)

    def test_prompt_handles_missing_optional_snapshot_fields(self):
        snapshot = {}
        files = [BundledFile(path="src/a.py", text="x=1\n", truncated=False)]
        q = "Review this"

        prompt = build_deep_review_prompt(snapshot, q, files)

        self.assertIn("File count:", prompt)
        self.assertIn("Languages:", prompt)
        self.assertIn("Frameworks:", prompt)
        self.assertIn("Collaboration:", prompt)
        self.assertIn(q, prompt)
        self.assertIn("FILE: src/a.py", prompt)


if __name__ == "__main__":
    unittest.main()
