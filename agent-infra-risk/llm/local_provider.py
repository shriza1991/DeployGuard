from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from .base import LLMProvider

logger = logging.getLogger("code-risk-llm")


class LocalProvider(LLMProvider):
    name = "local"

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 20):
        self.base_url = (base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1/chat/completions")).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama3.2")
        self.timeout = timeout

    def analyze(self, prompt: str) -> dict[str, Any]:
        response = requests.post(
            self.base_url,
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices")
        if not choices or not isinstance(choices, list):
            raise ValueError("Local LLM response lacked choices")

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("Local LLM response content was malformed")

        return json.loads(content)
