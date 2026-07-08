from __future__ import annotations

import os

from .base import LLMProvider
from .fallback_provider import FallbackProvider


def get_provider() -> LLMProvider:
    provider_name = (os.getenv("LLM_PROVIDER") or "fallback").strip().lower()

    if provider_name == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider()

    if provider_name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()

    if provider_name in {"ollama", "local", "lmstudio"}:
        from .local_provider import LocalProvider

        return LocalProvider()

    return FallbackProvider()
