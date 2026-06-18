"""Base LLM provider interface.

All LLM providers must implement this interface so the rest of the codebase
can remain provider-agnostic.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

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
