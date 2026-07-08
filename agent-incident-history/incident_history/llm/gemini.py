from __future__ import annotations

import json
import logging
import re
from typing import Any

from .provider import LLMProvider

logger = logging.getLogger("incident-history-agent")

_FENCE_OPEN = re.compile(r"^```(?:json)?\s*$", re.MULTILINE)
_FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        from google import genai
        from google.genai import types

        self.model = model
        self._types = types
        self._client = genai.Client(api_key=api_key)

    def analyze(self, prompt: str) -> dict[str, Any]:
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )
        logger.info("Gemini raw response: %s", response.text)
        if not response.text:
            raise ValueError("Gemini returned empty content")
        return _safe_json_parse(response.text)


def _safe_json_parse(content: str) -> dict[str, Any]:
    text = content.strip()
    open_match = _FENCE_OPEN.search(text)
    close_match = _FENCE_CLOSE.search(text)
    if open_match and close_match and open_match.start() < close_match.start():
        text = text[open_match.end(): close_match.start()].strip()
    if text.startswith("{"):
        return json.loads(text)
    start = text.find("{")
    if start < 0:
        raise ValueError("Gemini response contained no JSON object")
    depth = 0
    in_string = False
    escape_next = False
    for index, char in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise ValueError("Gemini response contained an unterminated JSON object")

