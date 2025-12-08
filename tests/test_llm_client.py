import os
import unittest

from capstone.llm_client import (
    DummyLlmClient,
    OpenAILlmClient,
    build_default_llm,
)


class LlmClientTests(unittest.TestCase):
    def setUp(self) -> None:
        # Remember the original api key so we can restore it.
        self._original_key = os.environ.get("OPENAI_API_KEY")

    def tearDown(self) -> None:
        # Restore the previous value after each test.
        if self._original_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self._original_key

    def test_dummy_llm_returns_prefixed_snippet(self) -> None:
        client = DummyLlmClient(prefix="[TEST]")
        prompt = "This is a very long prompt " * 30
        result = client.generate_summary(prompt)

        self.assertTrue(result.startswith("[TEST] "))
        # The dummy client should trim the prompt.
        self.assertLessEqual(len(result), 220)

    def test_build_default_llm_without_key_returns_none(self) -> None:
        os.environ.pop("OPENAI_API_KEY", None)
        client = build_default_llm()
        self.assertIsNone(client)

    def test_openai_client_without_key_skips_calls(self) -> None:
        os.environ.pop("OPENAI_API_KEY", None)
        client = OpenAILlmClient()
        # With no api key configured this should not raise and should
        # return an empty string so callers can fall back to offline logic.
        text = client.generate_summary("hello world")
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
