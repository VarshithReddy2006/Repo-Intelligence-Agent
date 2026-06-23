"""Base LLM provider interface.

All LLM providers must implement this interface so the rest of the codebase
can remain provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Health check result model
# ---------------------------------------------------------------------------

@dataclass
class ProviderHealth:
    """Health check result for a single LLM provider.

    Returned by every concrete provider's ``health_check()`` method.
    The caller (ProviderFactory.validate_all_providers) aggregates results
    to decide whether startup should proceed.

    Attributes:
        healthy:           True when the provider is reachable and authenticated.
        provider:          Provider name ("gemini", "deepseek", etc.)
        model:             Model identifier in use.
        authenticated:     True when credentials are accepted by the provider.
        latency_ms:        Round-trip latency of the health check call, if available.
        error_message:     Human-readable error description (no raw SDK strings).
        error_type:        ProviderErrorType value, or None on success.
        recommendation:    Actionable guidance for fixing the issue.
    """
    healthy: bool
    provider: str
    model: str
    authenticated: bool
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    recommendation: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Perform a lightweight health check to validate credentials.

        Contract:
          - MUST verify authentication with the remote API.
          - MUST NOT generate chat completions (use inexpensive API calls).
          - MUST complete within ~10 seconds.
          - MUST NOT raise exceptions — return ProviderHealth(healthy=False)
            with a classified error_type on failure.

        Returns:
            ProviderHealth with full diagnostic information.
        """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        response_mime_type: Optional[str] = None,
    ) -> str:
        """Generate a complete text response from the LLM.

        Args:
            prompt:               The user prompt / current message.
            system_instruction:   Optional system-level instruction prepended to the conversation.
            history:              Optional list of prior conversation turns in
                                  [{"role": "user"|"assistant", "content": "..."}] format.
            response_mime_type:   When "application/json", the model should return valid JSON.

        Returns:
            The generated text response as a string.
        """

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream token-by-token text output from the LLM.

        Args:
            prompt:             The user prompt / current message.
            system_instruction: Optional system-level instruction.
            history:            Optional list of prior conversation turns.

        Yields:
            Successive text chunks as they arrive from the provider.
        """
