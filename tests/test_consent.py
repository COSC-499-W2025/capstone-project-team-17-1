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
from capstone import consent as consent_module
from capstone.consent import (
    ConsentError,
    ExternalPermissionDenied,
    clear_external_permission,
    ensure_consent,
    ensure_external_permission,
    grant_consent,
    prompt_for_consent,
    request_external_service_permission,
    revoke_consent,
)


class ConsentFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        base_path = Path(self._tmpdir.name)
        config_dir = base_path / "config"
        config_path = config_dir / "user_config.json"
        log_dir = base_path / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        consent_log = log_dir / "consent_decisions.jsonl"
        self._patchers = [
            patch.object(config, "CONFIG_DIR", config_dir),
            patch.object(config, "CONFIG_PATH", config_path),
            patch.object(consent_module, "_LOG_DIR", log_dir),
            patch.object(consent_module, "_CONSENT_JOURNAL", consent_log),
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

    def test_external_permission_allow_once_does_not_persist(self) -> None:
        decisions = iter(["1"])
        outputs: list[str] = []

        granted = request_external_service_permission(
            "demo.service",
            data_types=["summary"],
            purpose="Generate insights",
            destination="https://example.com/api",
            input_fn=lambda _: next(decisions),
            output_fn=outputs.append,
        )

        self.assertTrue(granted)
        prefs = config.load_config().preferences
        self.assertEqual(prefs.external_permissions, {})
        log_file = consent_module._CONSENT_JOURNAL
        self.assertTrue(log_file.exists())
        entry = json.loads(log_file.read_text("utf-8").strip().splitlines()[-1])
        self.assertEqual(entry["decision"], "allow_once")
        self.assertFalse(entry["remember"])

    def test_external_permission_always_allow_is_remembered(self) -> None:
        granted = request_external_service_permission(
            "demo.service",
            data_types=["metadata"],
            purpose="Remote processing",
            destination="https://example.com",
            input_fn=lambda _: "2",
            output_fn=lambda _: None,
        )
        self.assertTrue(granted)
        prefs = config.load_config().preferences
        self.assertIn("demo.service", prefs.external_permissions)
        stored = prefs.external_permissions["demo.service"]
        self.assertTrue(stored["granted"])
        self.assertTrue(stored["remember"])
        self.assertEqual(stored["decision"], "allow_always")

        def fail_prompt(_: str) -> str:
            raise AssertionError("Prompt should not be triggered for remembered decisions")

        auto = request_external_service_permission(
            "demo.service",
            data_types=["metadata"],
            purpose="Remote processing",
            destination="https://example.com",
            input_fn=fail_prompt,
            output_fn=lambda _: None,
        )
        self.assertTrue(auto)

    def test_external_permission_deny_this_session_does_not_persist(self) -> None:
        granted = request_external_service_permission(
            "demo.service",
            data_types=["metadata"],
            purpose="Remote processing",
            destination="https://example.com",
            input_fn=lambda _: "3",
            output_fn=lambda _: None,
        )
        self.assertFalse(granted)
        prefs = config.load_config().preferences
        self.assertEqual(prefs.external_permissions, {})
        log_file = consent_module._CONSENT_JOURNAL
        entry = json.loads(log_file.read_text("utf-8").strip().splitlines()[-1])
        self.assertEqual(entry["decision"], "deny_once")
        self.assertFalse(entry["remember"])

    def test_external_permission_deny_always_blocks_future_requests(self) -> None:
        granted = request_external_service_permission(
            "demo.service",
            data_types=["metadata"],
            purpose="Remote processing",
            destination="https://example.com",
            input_fn=lambda _: "4",
            output_fn=lambda _: None,
        )
        self.assertFalse(granted)
        prefs = config.load_config().preferences
        stored = prefs.external_permissions["demo.service"]
        self.assertFalse(stored["granted"])
        self.assertTrue(stored["remember"])
        self.assertEqual(stored["decision"], "deny_always")

        with self.assertRaises(ExternalPermissionDenied):
            ensure_external_permission(
                "demo.service",
                data_types=["metadata"],
                purpose="Remote processing",
                destination="https://example.com",
                input_fn=lambda _: "ignored",
                output_fn=lambda _: None,
            )

        clear_external_permission("demo.service")
        prefs_after = config.load_config().preferences
        self.assertNotIn("demo.service", prefs_after.external_permissions)


if __name__ == "__main__":
    unittest.main()
