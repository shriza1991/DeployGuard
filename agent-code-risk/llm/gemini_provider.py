from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai import types

from .base import LLMProvider

logger = logging.getLogger("code-risk-llm")

# Matches an opening ``` or ```json fence line.
_FENCE_OPEN = re.compile(r"^```(?:json)?\s*$", re.MULTILINE)
# Matches a closing ``` fence line.
_FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)


def _safe_json_parse(content: str) -> dict[str, Any]:
    """Extract and parse the first valid JSON object from *content*.

    Handles the common Gemini formatting quirks in order:
    1. Strip surrounding whitespace.
    2. Strip Markdown code fences (```json ... ``` or ``` ... ```).
    3. Find the first ``{`` and scan forward to the matching ``}`` using a
       depth counter — this tolerates leading/trailing explanatory text.
    4. Parse the extracted slice with ``json.loads``.

    Raises ``ValueError`` (never silently returns) if no valid JSON object
    can be extracted.
    """
    text = content.strip()
    if not text:
        raise ValueError("Gemini returned empty content")

    # --- Step 1: strip markdown code fences ---
    # If the response is wrapped in ```...``` or ```json...```, pull out the
    # inner block so json.loads doesn't see the backticks.
    open_match = _FENCE_OPEN.search(text)
    close_match = _FENCE_CLOSE.search(text)
    if open_match and close_match and open_match.start() < close_match.start():
        text = text[open_match.end(): close_match.start()].strip()

    # --- Step 2: fast-path for a clean JSON object ---
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass  # fall through to the depth-scan

    # --- Step 3: depth-scan to find the first balanced { ... } ---
    start = text.find("{")
    if start == -1:
        raise ValueError("Gemini response contained no JSON object")

    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start: i + 1]
                return json.loads(candidate)

    raise ValueError("Gemini response contained an unterminated JSON object")


class GeminiProvider(LLMProvider):
    """Uses the official Google Gen AI SDK (google-genai) to call Gemini.

    A single ``genai.Client`` is created at construction time and reused for
    every ``analyze()`` call.  Generation settings are passed through
    ``types.GenerateContentConfig``.  ``response_mime_type="application/json"``
    asks the model to emit a raw JSON object rather than wrapping it in
    Markdown fences — reducing (but not eliminating) the need for fence
    stripping in ``_safe_json_parse``.

    Exceptions are *not* swallowed — they propagate so the retry loop in
    ``LLMReasoner._generate_with_retries`` handles them uniformly.
    """

    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        if not self.api_key:
            logger.warning("Gemini provider configured but GEMINI_API_KEY is missing.")
            raise ValueError("GEMINI_API_KEY is not configured")

        # One client instance reused across all calls — no reconnection overhead.
        self._client = genai.Client(api_key=self.api_key)

    def analyze(self, prompt: str) -> dict[str, Any]:
        logger.debug("Sending prompt to Gemini model %s", self.model)

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                    # Ask the model to return a raw JSON object, not Markdown.
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            # Log and re-raise so the retry mechanism in LLMReasoner handles it.
            logger.warning("Gemini SDK call failed: %s: %s", type(exc).__name__, exc)
            raise

        text = response.text
        # Always log the raw response so parsing failures are diagnosable.
        logger.info("Gemini raw response:\n%s", text)

        if not text:
            raise ValueError("Gemini returned an empty response")

        try:
            return _safe_json_parse(text)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "Gemini response parsing failed: %s\nRaw response was:\n%s",
                exc,
                text,
            )
            raise ValueError("Gemini returned invalid JSON") from exc
