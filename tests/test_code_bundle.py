import io
import sys
import unittest
import tempfile
from pathlib import Path
from zipfile import ZipFile

# Ensure src is importable when running tests directly
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone.code_bundle import bundle_code_from_zip


class TestCodeBundle(unittest.TestCase):
    def _make_zip(self, zip_path: Path, files: dict[str, bytes]) -> None:
        with ZipFile(zip_path, "w") as z:
            for name, content in files.items():
                z.writestr(name, content)

    def test_bundles_only_included_paths_and_text_exts(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zpath = td_path / "proj.zip"

            self._make_zip(
                zpath,
                {
                    "src/a.py": b"print('hello')\n",
                    "src/b.txt": b"this should not be included by ext\n",
                    "src/c.js": b"console.log('x')\n",
                    "assets/logo.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 50,
                },
            )

            bundled = bundle_code_from_zip(
                zpath,
                include_paths=["src/a.py", "src/b.txt", "src/c.js", "assets/logo.png"],
            )

            paths = [b.path for b in bundled]
            self.assertIn("src/a.py", paths)
            self.assertIn("src/c.js", paths)

            # .txt is not in TEXT_EXTS in the implementation you posted
            self.assertNotIn("src/b.txt", paths)

            # binary file should be excluded
            self.assertNotIn("assets/logo.png", paths)

    def test_redacts_lines_with_secret_hints(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zpath = td_path / "proj.zip"

            code = (
                "def f():\n"
                "    api_key = 'SUPERSECRET'\n"
                "    return 1\n"
            ).encode("utf-8")

            self._make_zip(zpath, {"src/secrets.py": code})

            bundled = bundle_code_from_zip(zpath, include_paths=["src/secrets.py"])
            self.assertEqual(len(bundled), 1)

            text = bundled[0].text
            self.assertIn("[REDACTED LINE POSSIBLE SECRET]", text)
            self.assertNotIn("SUPERSECRET", text)

    def test_truncates_per_file_limit(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zpath = td_path / "proj.zip"

            big = ("a" * 200).encode("utf-8")
            self._make_zip(zpath, {"src/big.py": big})

            bundled = bundle_code_from_zip(
                zpath,
                include_paths=["src/big.py"],
                max_file_chars=50,
                max_total_chars=1000,
            )
            self.assertEqual(len(bundled), 1)
            self.assertEqual(len(bundled[0].text), 50)
            self.assertTrue(bundled[0].truncated)

    def test_truncates_when_total_limit_hit(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zpath = td_path / "proj.zip"

            self._make_zip(
                zpath,
                {
                    "src/one.py": b"1" * 80,
                    "src/two.py": b"2" * 80,
                },
            )

            bundled = bundle_code_from_zip(
                zpath,
                include_paths=["src/one.py", "src/two.py"],
                max_files=10,
                max_total_chars=120,
                max_file_chars=10_000,
            )

            self.assertEqual(len(bundled), 2)
            total = sum(len(b.text) for b in bundled)
            self.assertLessEqual(total, 120)

            # At least one entry should be truncated due to total cap
            self.assertTrue(any(b.truncated for b in bundled))

    def test_respects_max_files(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zpath = td_path / "proj.zip"

            self._make_zip(
                zpath,
                {
                    "src/a.py": b"a",
                    "src/b.py": b"b",
                    "src/c.py": b"c",
                },
            )

            bundled = bundle_code_from_zip(
                zpath,
                include_paths=["src/a.py", "src/b.py", "src/c.py"],
                max_files=2,
                max_total_chars=1000,
            )

            self.assertEqual(len(bundled), 2)


if __name__ == "__main__":
    unittest.main()
