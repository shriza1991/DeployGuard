from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

logger = logging.getLogger("code-risk-llm")

DEFAULT_PROMPT_TEMPLATE = """You are reviewing a deployment risk assessment for a code change.

Deterministic analyzer findings:
{deterministic_json}

Git diff context:
{diff_text}

Your job is to enrich the analysis, not replace it.
Rules:
- Do not invent facts or vulnerabilities.
- Do not ignore the deterministic findings.
- Keep the deterministic score authoritative.
- Focus on higher-level deployment risk, rollout strategy, and mitigation guidance.
- If evidence is weak, keep the confidence adjustment small and conservative.

Return valid JSON with this shape:
{{
  "summary": "short explanation of why the deployment may be risky",
  "additional_risks": ["risk 1", "risk 2"],
  "deployment_recommendation": "recommended rollout strategy or mitigation",
  "confidence_adjustment": 0.08,
  "risk_adjustment": 5,
  "reasoning": "brief explanation of the reasoning"
}}
"""


class ReasoningProvider(ABC):
    name = "base"

    @abstractmethod
    def generate_reasoning(self, prompt: str) -> dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(ReasoningProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    def generate_reasoning(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": "You are a careful deployment risk reviewer."}, {"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return _parse_json_response(content)


class GeminiProvider(ReasoningProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def generate_reasoning(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_response(content)


class LocalProvider(ReasoningProvider):
    name = "local"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1/chat/completions")).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama3.2")

    def generate_reasoning(self, prompt: str) -> dict[str, Any]:
        response = requests.post(
            self.base_url,
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return _parse_json_response(content)


class NullProvider(ReasoningProvider):
    name = "disabled"

    def generate_reasoning(self, prompt: str) -> dict[str, Any]:
        raise ValueError("LLM provider is not configured")


class LLMReasoner:
    def __init__(self, provider: ReasoningProvider | None = None, cache_ttl_seconds: int = 300):
        self.provider = provider or _build_provider()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def reason_about_change(self, payload: dict[str, Any], deterministic_result: dict[str, Any]) -> dict[str, Any]:
        diff_text = _extract_diff_text(payload)
        prompt = DEFAULT_PROMPT_TEMPLATE.format(
            deterministic_json=json.dumps(deterministic_result, indent=2),
            diff_text=diff_text or "No diff text was provided.",
        )

        cache_key = self._cache_key(payload, deterministic_result)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        response = self._generate_with_retries(prompt)
        self._cache[cache_key] = (time.time(), response)
        return response

    def _generate_with_retries(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.provider.generate_reasoning(prompt)
                return _normalize_response(response)
            except requests.Timeout as exc:
                last_error = exc
                logger.warning("LLM request timed out (attempt %s/3): %s", attempt + 1, exc)
            except requests.HTTPError as exc:
                last_error = exc
                logger.warning("LLM request failed (attempt %s/3): %s", attempt + 1, exc)
            except requests.ConnectionError as exc:
                last_error = exc
                logger.warning("LLM connection failed (attempt %s/3): %s", attempt + 1, exc)
            except ValueError as exc:
                last_error = exc
                logger.warning("LLM response was invalid (attempt %s/3): %s", attempt + 1, exc)
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning("LLM returned malformed JSON (attempt %s/3): %s", attempt + 1, exc)

            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))

        logger.warning("LLM reasoning unavailable after retries: %s", last_error)
        return _default_response()

    def _cache_key(self, payload: dict[str, Any], deterministic_result: dict[str, Any]) -> str:
        stable_payload = {
            "payload": payload,
            "deterministic": deterministic_result,
        }
        encoded = json.dumps(stable_payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _build_provider() -> ReasoningProvider:
    provider_name = (os.getenv("LLM_PROVIDER") or "disabled").lower()
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "gemini":
        return GeminiProvider()
    if provider_name in {"local", "ollama", "lmstudio"}:
        return LocalProvider()
    return NullProvider()


def _extract_diff_text(payload: dict[str, Any]) -> str:
    payload_diff = payload.get("diff")
    if isinstance(payload_diff, str) and payload_diff:
        return payload_diff

    parts: list[str] = []
    for file_entry in payload.get("files", []) or []:
        patch = file_entry.get("patch")
        if patch:
            parts.append(f"### {file_entry.get('filename', 'unknown')}\n{patch}")
    return "\n\n".join(parts)


def _parse_json_response(content: str) -> dict[str, Any]:
    if not content:
        raise ValueError("LLM returned empty content")

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(content)


def _normalize_response(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ValueError("LLM response was not a JSON object")

    normalized = {
        "summary": str(response.get("summary") or "Deterministic analysis reviewed with conservative AI context."),
        "additional_risks": [str(item) for item in response.get("additional_risks", []) if str(item).strip()],
        "deployment_recommendation": str(response.get("deployment_recommendation") or "Use the deterministic findings and follow standard rollout safeguards."),
        "confidence_adjustment": float(response.get("confidence_adjustment", 0.0) or 0.0),
        "risk_adjustment": int(response.get("risk_adjustment", 0) or 0),
        "reasoning": str(response.get("reasoning") or "The LLM reviewed the diff and analyzer output."),
        "provider": response.get("provider") or "unknown",
        "available": True,
    }

    normalized["confidence_adjustment"] = max(-0.2, min(0.2, normalized["confidence_adjustment"]))
    normalized["risk_adjustment"] = max(-10, min(10, normalized["risk_adjustment"]))
    return normalized


def _default_response() -> dict[str, Any]:
    return {
        "summary": "Deterministic analyzers were used to assess the change because the AI reasoning layer was unavailable.",
        "additional_risks": [],
        "deployment_recommendation": "Proceed with standard deployment safeguards and review the deterministic findings.",
        "confidence_adjustment": 0.0,
        "risk_adjustment": 0,
        "reasoning": "The LLM service was unavailable or returned an invalid response, so the deterministic analysis remains authoritative.",
        "provider": "unavailable",
        "available": False,
    }
