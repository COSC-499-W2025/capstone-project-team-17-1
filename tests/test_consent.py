import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import config
from capstone.consent import (
    ConsentError,
    ensure_consent,
    grant_consent,
    prompt_for_consent,
    revoke_consent,
)


class ConsentFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        config_dir = Path(self._tmpdir.name) / "config"
        config_path = config_dir / "user_config.json"
        self._patchers = [
            patch.object(config, "CONFIG_DIR", config_dir),
            patch.object(config, "CONFIG_PATH", config_path),
        ]
        for patcher in self._patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._tmpdir.cleanup)

    def test_consent_required_before_processing(self) -> None:
        with self.assertRaises(ConsentError):
            ensure_consent()

        grant_consent()
        state = ensure_consent()
        self.assertTrue(state.granted)

        revoke_consent()
        state = config.load_config().consent
        self.assertFalse(state.granted)
        stored = Path(config.CONFIG_PATH)
        self.assertTrue(stored.exists())
        payload = json.loads(stored.read_text("utf-8"))
        self.assertIn("consent", payload)

    def test_prompt_for_consent_reprompts_until_valid(self) -> None:
        inputs = iter(["maybe", "Y"])
        messages: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(message: str) -> None:
            messages.append(message)

        result = prompt_for_consent(fake_input, fake_output)
        self.assertEqual(result, "accepted")
        self.assertTrue(any("Invalid input" in msg for msg in messages))

        inputs_decline = iter(["no"])
        result_decline = prompt_for_consent(lambda _: next(inputs_decline), fake_output)
        self.assertEqual(result_decline, "rejected")


if __name__ == "__main__":
    unittest.main()
