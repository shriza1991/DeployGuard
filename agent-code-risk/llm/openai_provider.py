from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from .base import LLMProvider

logger = logging.getLogger("code-risk-llm")


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None, timeout: int = 20):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.timeout = timeout

    def analyze(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            logger.warning("OpenAI provider configured but OPENAI_API_KEY is missing.")
            raise ValueError("OPENAI_API_KEY is not configured")

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a careful deployment risk reviewer."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices")
        if not choices or not isinstance(choices, list):
            raise ValueError("OpenAI response lacked choices")

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("OpenAI response content was malformed")

        return json.loads(content)
