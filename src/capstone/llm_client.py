import os
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMClient:
    """Thin wrapper around an LLM provider (raises if not configured)."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        if OpenAI is None:
            raise RuntimeError("openai package is not installed")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def ask(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a technical project analysis assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


class DummyLlmClient:
    """Offline-friendly LLM stub used in tests and dry-runs."""

    def __init__(self, prefix: str = "[LLM]") -> None:
        self.prefix = prefix

    def generate_summary(self, prompt: str) -> str:
        snippet = " ".join((prompt or "").split())
        max_total = 220
        available = max_total - len(self.prefix) - 1
        if available < 0:
            return self.prefix[:max_total]
        if len(snippet) > available:
            snippet = snippet[:available].rstrip()
        return f"{self.prefix} {snippet}".rstrip()


class OpenAILlmClient:
    """OpenAI client that safely no-ops when not configured."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = OpenAI(api_key=self.api_key) if self.api_key and OpenAI is not None else None

    def generate_summary(self, prompt: str) -> str:
        if not self._client:
            return ""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a technical project analysis assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception:
            return ""
        content = response.choices[0].message.content
        return content.strip() if content else ""


def build_default_llm() -> Optional[OpenAILlmClient]:
    """Return a configured OpenAI client, or None when unavailable."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    if OpenAI is None:
        return None
    return OpenAILlmClient()


__all__ = [
    "DummyLlmClient",
    "LLMClient",
    "OpenAILlmClient",
    "build_default_llm",
]
