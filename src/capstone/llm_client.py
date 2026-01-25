import os
from typing import Dict, Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMClient:
    """
    Thin wrapper around an LLM provider.
    Stateless by design.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
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
