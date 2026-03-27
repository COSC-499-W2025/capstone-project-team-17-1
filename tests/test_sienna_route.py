from __future__ import annotations

from contextlib import contextmanager
import unittest
from fastapi import HTTPException

from capstone.api.routes import sienna
from capstone.api.routes.sienna import SiennaChatRequest, SiennaChatMessage


class _DummyRequest:
    headers: dict[str, str] = {}


@contextmanager
def _dummy_db_session(_db_dir):
    yield object()


class SiennaRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_openai = sienna.OpenAI
        self._orig_api_key = sienna.os.getenv("OPENAI_API_KEY")

    def tearDown(self) -> None:
        sienna.OpenAI = self._orig_openai
        if self._orig_api_key is None:
            sienna.os.environ.pop("OPENAI_API_KEY", None)
        else:
            sienna.os.environ["OPENAI_API_KEY"] = self._orig_api_key

    def test_is_debug_intent_detection(self):
        self.assertTrue(sienna._is_debug_intent("please debug this crash", False))
        self.assertFalse(sienna._is_debug_intent("normal project summary please", False))
        self.assertTrue(sienna._is_debug_intent("any question", True))

    def test_is_off_topic_detection(self):
        self.assertTrue(sienna._is_off_topic("what is the weather today"))
        self.assertFalse(sienna._is_off_topic("debug weather API issue in my project"))

    def test_synthesize_openai_voice_none_when_unavailable(self):
        sienna.os.environ["OPENAI_API_KEY"] = "x"
        sienna.OpenAI = None
        self.assertIsNone(sienna._synthesize_openai_voice("hello world"))

    def test_synthesize_openai_voice_success(self):
        sienna.os.environ["OPENAI_API_KEY"] = "x"

        class _Resp:
            def read(self):
                return b"\x01\x02\x03"

        class _Speech:
            @staticmethod
            def create(**_kwargs):
                return _Resp()

        class _Audio:
            speech = _Speech()

        class _Client:
            def __init__(self, *args, **kwargs):
                self.audio = _Audio()

        sienna.OpenAI = _Client
        result = sienna._synthesize_openai_voice("hello world")
        self.assertIsNotNone(result)
        self.assertEqual(result["audio_base64"], "AQID")
        self.assertEqual(result["audio_format"], "mp3")
        self.assertIn(result["voice"], {"nova", "alloy"})

    def test_ask_sienna_off_topic_returns_restricted_payload(self):
        payload = SiennaChatRequest(
            message="what is the weather in toronto?",
            project_id="demo",
            history=[],
            debug=False,
        )

        orig_restore = sienna._restore_user_from_request
        orig_tts = sienna._synthesize_openai_voice
        try:
            sienna._restore_user_from_request = lambda _request: None
            sienna._synthesize_openai_voice = lambda _text: None
            out = sienna.ask_sienna(payload, _DummyRequest())
            self.assertEqual(out["context_mode"], "restricted")
            self.assertEqual(out["reply"], "I can only help with your Loom projects or Loom features.")
            self.assertIsNone(out["audio"])
        finally:
            sienna._restore_user_from_request = orig_restore
            sienna._synthesize_openai_voice = orig_tts

    def test_ask_sienna_raises_when_external_consent_denied(self):
        payload = SiennaChatRequest(
            message="explain this project",
            project_id="demo",
            history=[],
            debug=False,
        )
        orig_restore = sienna._restore_user_from_request
        orig_ensure = sienna.ensure_external_permission
        try:
            sienna._restore_user_from_request = lambda _request: None

            def _deny(_service):
                raise sienna.ExternalPermissionDenied("denied")

            sienna.ensure_external_permission = _deny
            with self.assertRaises(HTTPException) as exc:
                sienna.ask_sienna(payload, _DummyRequest())
            self.assertEqual(exc.exception.status_code, 403)
        finally:
            sienna._restore_user_from_request = orig_restore
            sienna.ensure_external_permission = orig_ensure

    def test_ask_sienna_success_debug_path(self):
        payload = SiennaChatRequest(
            message="debug issue in app.py",
            project_id="demo-project",
            history=[
                SiennaChatMessage(role="user", content="previous user message"),
                SiennaChatMessage(role="assistant", content="previous assistant message"),
            ],
            debug=False,
        )

        project = sienna._ProjectContext(
            project_id="demo-project",
            snapshot={"skills": {"python": 5}, "file_summary": {"file_count": 12}},
            classification="individual",
            primary_contributor="alice",
            created_at="2026-01-01",
            zip_path=None,
        )

        orig_restore = sienna._restore_user_from_request
        orig_ensure = sienna.ensure_external_permission
        orig_db = sienna._db_session
        orig_load = sienna._load_project_context
        orig_collect = sienna._collect_relevant_code_snippets
        orig_call = sienna._call_openai
        orig_tts = sienna._synthesize_openai_voice
        try:
            sienna._restore_user_from_request = lambda _request: None
            sienna.ensure_external_permission = lambda _service: None
            sienna._db_session = _dummy_db_session
            sienna._load_project_context = lambda _conn, _pid: project
            sienna._collect_relevant_code_snippets = (
                lambda _conn, _project, _message: [{"path": "app.py", "content": "print('ok')"}]
            )
            sienna._call_openai = lambda _messages: "Sienna response text"
            sienna._synthesize_openai_voice = (
                lambda _text: {"audio_base64": "AQID", "audio_format": "mp3", "voice": "nova"}
            )

            out = sienna.ask_sienna(payload, _DummyRequest())
            self.assertEqual(out["project_id"], "demo-project")
            self.assertEqual(out["reply"], "Sienna response text")
            self.assertEqual(out["context_mode"], "debug")
            self.assertEqual(out["used_files"], ["app.py"])
            self.assertEqual(out["audio"], "AQID")
            self.assertEqual(out["audio_format"], "mp3")
        finally:
            sienna._restore_user_from_request = orig_restore
            sienna.ensure_external_permission = orig_ensure
            sienna._db_session = orig_db
            sienna._load_project_context = orig_load
            sienna._collect_relevant_code_snippets = orig_collect
            sienna._call_openai = orig_call
            sienna._synthesize_openai_voice = orig_tts

    def test_synthesize_voice_endpoint_returns_empty_on_failure(self):
        payload = sienna.SiennaVoiceRequest(text="hello")
        orig_restore = sienna._restore_user_from_request
        orig_ensure = sienna.ensure_external_permission
        orig_tts = sienna._synthesize_openai_voice
        try:
            sienna._restore_user_from_request = lambda _request: None
            sienna.ensure_external_permission = lambda _service: None
            sienna._synthesize_openai_voice = lambda _text: None
            out = sienna.synthesize_sienna_voice(payload, _DummyRequest())
            self.assertEqual(out, {"audio": None, "audio_format": None, "voice": None})
        finally:
            sienna._restore_user_from_request = orig_restore
            sienna.ensure_external_permission = orig_ensure
            sienna._synthesize_openai_voice = orig_tts


if __name__ == "__main__":
    unittest.main()
