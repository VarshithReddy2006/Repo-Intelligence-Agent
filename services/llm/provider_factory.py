"""Provider factory — single entry-point for obtaining the configured LLM provider.

Usage:
    from services.llm import ProviderFactory
    provider = ProviderFactory.get_provider()
    answer = await provider.generate(prompt, system_instruction=...)
"""

import os
import logging
from typing import Optional
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

_cached_provider: Optional[BaseLLMProvider] = None


class ProviderFactory:
    """Creates and caches the globally configured LLM provider instance."""

    @classmethod
    def get_provider(cls) -> BaseLLMProvider:
        """Return the singleton provider instance, creating it if necessary.

        The active provider is selected by the LLM_PROVIDER environment variable
        (default: "deepseek"). Supported values: "deepseek".
        """
        global _cached_provider
        if _cached_provider is not None:
            return _cached_provider

        provider_name = os.environ.get("LLM_PROVIDER", "deepseek").lower().strip()

        if provider_name == "deepseek":
            from .deepseek_provider import DeepSeekProvider
            _cached_provider = DeepSeekProvider()
            logger.info(
                "LLM provider initialised: DeepSeek (%s) via NVIDIA NIM",
                os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/deepseek-v4-flash"),
            )
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{provider_name}'. Supported values: 'deepseek'."
            )

        return _cached_provider

    @classmethod
    def reset(cls) -> None:
        """Clear the cached provider (useful for testing or reconfiguration)."""
        global _cached_provider
        _cached_provider = None
