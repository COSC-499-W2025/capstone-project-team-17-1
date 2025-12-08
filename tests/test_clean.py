from pathlib import Path
import os, subprocess, sys

REPO_ROOT = Path(__file__).resolve().parents[1]  # repo root (folder that contains src/)

def test_clean_removes_dir(tmp_path):
    target = tmp_path / "analysis_output"
    target.mkdir()
    (target / "x.txt").write_text("x")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")  # ensure capstone import works

    # Run CLI with cwd=tmp_path so our safety check allows deletion
    out = subprocess.check_output(
        [sys.executable, "-m", "capstone.cli", "clean", "--path", str(target)],
        cwd=str(tmp_path),
        env=env,
    ).decode()

    assert "Removed directory" in out
    assert not target.exists()
