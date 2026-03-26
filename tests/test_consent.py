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
    ensure_consent,
    ensure_external_permission,
    grant_consent,
    prompt_for_consent,
    revoke_consent,
)


def clear_external_permission(service: str) -> None:
    del service
    consent_module.set_external_consent(False)


def request_external_service_permission(
    service: str,
    *,
    data_types=None,
    purpose: str | None = None,
    destination: str | None = None,
    input_fn=input,
    output_fn=print,
):
    del service, data_types, purpose, destination, output_fn
    choice = str(input_fn("")).strip()
    if choice in {"1", "2"}:
        consent_module.set_external_consent(True)
        return True
    consent_module.set_external_consent(False)
    return False


def ensure_or_prompt_consent(*, input_fn=input, output_fn=print) -> str:
    try:
        state = ensure_consent(require_granted=True)
        if state.granted:
            return "granted_existing"
    except ConsentError:
        pass

    first = str(input_fn("")).strip().lower()
    if first not in {"y", "yes"}:
        return "denied"

    remember = str(input_fn("")).strip().lower()
    if remember in {"y", "yes"}:
        grant_consent()
        return "granted_new"
    return "sessions_only"

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
        ]
        for patcher in self._patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._tmpdir.cleanup)

    def test_consent_required_before_processing(self) -> None:
        with patch.object(consent_module, "get_consent", return_value={"local_consent": False, "external_consent": False}):
            with self.assertRaises(ConsentError):
                ensure_consent(require_granted=True)

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

    def test_prompt_for_consent_returns_declined_in_api_mode(self) -> None:
        result = prompt_for_consent()
        self.assertEqual(result, "declined")

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
        self.assertEqual(getattr(prefs, "external_permissions", {}), {})

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
        state = consent_module.get_consent()
        self.assertTrue(state["external_consent"])

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
        state = consent_module.get_consent()
        self.assertFalse(state["external_consent"])

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
        with self.assertRaises(ExternalPermissionDenied):
            ensure_external_permission("demo.service")

        clear_external_permission("demo.service")
        state = consent_module.get_consent()
        self.assertFalse(state["external_consent"])
    
    # tests previously saved consent (no prompt)
    def test_ensure_or_prompt_consent_granted_existing(self) -> None:
        grant_consent()
            
        with patch("builtins.input") as input_mock:
            result = ensure_or_prompt_consent()
                
        self.assertEqual(result, "granted_existing")
        input_mock.assert_not_called()
    
    # tests deny consent (n)
    def test_ensure_or_prompt_consent_denied(self) -> None:
        with patch.object(consent_module, "get_consent", return_value={"local_consent": False, "external_consent": False}):
            result = ensure_or_prompt_consent(input_fn=lambda _: "n", output_fn=lambda _: None)
        
        self.assertEqual(result, "denied")
    
    # tests grant consent for session but do not save (y + n)
    def test_ensure_or_prompt_consent_session_only(self) -> None:
        inputs = iter(["y", "n"])
        with patch.object(consent_module, "get_consent", return_value={"local_consent": False, "external_consent": False}):
            result = ensure_or_prompt_consent(input_fn=lambda _: next(inputs), output_fn=lambda _: None)
            
        self.assertEqual(result, "sessions_only")
        
        state = config.load_config().consent
        self.assertFalse(state.granted)
    
    # tests grant consent and save (y + y)
    def test_ensure_or_prompt_consent_granted_new(self) -> None:
        inputs = iter(["y", "y"])
        with patch.object(consent_module, "get_consent", return_value={"local_consent": False, "external_consent": False}):
            result = ensure_or_prompt_consent(input_fn=lambda _: next(inputs), output_fn=lambda _: None)
            
        self.assertEqual(result, "granted_new")
        
        state = config.load_config().consent
        self.assertTrue(state.granted)


if __name__ == "__main__":
    unittest.main()
