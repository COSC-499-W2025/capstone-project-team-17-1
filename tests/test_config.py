import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from capstone import config  # noqa: E402


class ConfigModuleTestCase(unittest.TestCase):
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

    def _load_raw_payload(self) -> dict:
        with config.CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def test_first_load_creates_encrypted_defaults(self) -> None:
        cfg = config.load_config()
        self.assertFalse(cfg.consent.granted)
        self.assertEqual(cfg.preferences.analysis_mode, "local")

        stored = self._load_raw_payload()
        self.assertIn("consent", stored)
        self.assertIsInstance(stored["consent"], str)
        decrypted = config._decrypt(stored["consent"])  # type: ignore[attr-defined]
        self.assertEqual(decrypted["granted"], False)

    def test_update_preferences_merges_known_fields(self) -> None:
        config.load_config()
        updated = config.update_preferences(theme="dark", analysis_mode="external", invalid_field="ignored")
        self.assertEqual(updated.preferences.theme, "dark")
        self.assertEqual(updated.preferences.analysis_mode, "external")
        with self.assertRaises(AttributeError):
            getattr(updated.preferences, "invalid_field")

        stored = self._load_raw_payload()
        decrypted = config._decrypt(stored["preferences"])  # type: ignore[attr-defined]
        self.assertEqual(decrypted["theme"], "dark")
        self.assertNotIn("invalid_field", decrypted)

    def test_update_consent_overwrites_timestamp(self) -> None:
        config.load_config()
        with patch("capstone.config.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            updated = config.update_consent(granted=True, decision="allow", source="test")

        self.assertTrue(updated.consent.granted)
        self.assertEqual(updated.consent.decision, "allow")
        self.assertEqual(updated.consent.source, "test")
        self.assertTrue(updated.consent.timestamp.startswith("2024-01-01T12:00:00"))

    def test_reset_config_restores_defaults(self) -> None:
        config.update_preferences(theme="dark")
        reset = config.reset_config()
        self.assertEqual(reset.preferences.theme, "light")
        self.assertFalse(reset.consent.granted)

        payload = self._load_raw_payload()
        decrypted = config._decrypt(payload["preferences"])  # type: ignore[attr-defined]
        self.assertEqual(decrypted["theme"], "light")

    def test_validate_config_shape_enforces_structure(self) -> None:
        config.load_config()
        payload = self._load_raw_payload()
        config.validate_config_shape(payload)

        with self.assertRaises(ValueError):
            config.validate_config_shape({"consent": "not_encrypted"})

        bad_payload = payload.copy()
        bad_payload["consent"] = config._encrypt({"granted": True})  # type: ignore[attr-defined]
        with self.assertRaises(ValueError):
            config.validate_config_shape(bad_payload)


if __name__ == "__main__":
    unittest.main()
