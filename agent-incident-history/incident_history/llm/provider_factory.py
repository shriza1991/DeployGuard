from __future__ import annotations

import logging

from incident_history.config import Settings
from incident_history.llm.fallback import FallbackLLMProvider
from incident_history.llm.provider import LLMProvider

logger = logging.getLogger("incident-history-agent")


def get_llm_provider(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "gemini":
        try:
            from incident_history.llm.gemini import GeminiProvider

            return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        except Exception as exc:
            logger.warning("Gemini unavailable, using fallback provider: %s", exc)
            return FallbackLLMProvider()
    return FallbackLLMProvider()

