from __future__ import annotations

import os
from typing import Optional

from .logging_utils import get_logger

logger = get_logger(__name__)

try:
    # will use it in try just in case someone don't have openapi library installed
    from openai import OpenAI  
except Exception:  
    OpenAI = None  


class OpenAILlmClient:
    """
    Thin wrapper around the OpenAI Responses API.

    It exposes a single method, generate_summary, which matches
    what AutoWriter expects in top_project_summaries.
    """

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self._model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or OpenAI is None:
            # No api key or library not installed, run in no network mode.
            logger.warning(
                "OpenAILlmClient initialised without OpenAI configuration, "
                "LLM calls will be skipped."
            )
            self._client = None
        else:
            # The OpenAI client reads the api key from the environment.
            self._client = OpenAI()

    def generate_summary(self, prompt: str) -> str:
        """
        Return a short summary string for the given prompt.

        If the client is not configured or the call fails, this
        method returns an empty string so callers can fall back
        to offline summaries.
        """
        if self._client is None:
            logger.info("Skipping LLM call because client is not configured")
            return ""

        try:
            response = self._client.responses.create(
                model=self._model,
                input=prompt,
                max_output_tokens=400,
            )
            text = getattr(response, "output_text", None)
            if text is not None:
                return text
            # Fallback in case output_text is not present.
            try:
                return response.output[0].content[0].text  # type: ignore[no-any-return]
            except Exception:
                return ""
        except Exception as exc:  
            logger.warning("OpenAI LLM call failed: %s", exc)
            return ""


class DummyLlmClient:
    """
    Offline test double for the LLM client.

    This never touches the network and lets us exercise the
    rest of the pipeline during development and in unit tests.
    """

    def __init__(self, prefix: str = "[DUMMY LLM]") -> None:
        self._prefix = prefix

    def generate_summary(self, prompt: str) -> str:
        # Compact the prompt to a single line and trim it so
        # test output stays small and predictable.
        snippet = " ".join(prompt.split())
        max_len = 200
        if len(snippet) > max_len:
            snippet = snippet[: max_len - 3] + "..."
        return f"{self._prefix} {snippet}"


def build_default_llm() -> Optional[object]:
    """
    Factory used by higher level code.

    When an api key and library are available, this returns
    an OpenAILlmClient instance. Otherwise it returns None
    so callers can decide whether to fall back to offline
    summaries or a DummyLlmClient.
    """
    if OpenAI is None:
        return None
    if not os.getenv("OPENAI_API_KEY"):
        return None
    return OpenAILlmClient()
