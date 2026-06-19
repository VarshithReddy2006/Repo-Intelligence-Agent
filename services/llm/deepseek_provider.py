"""DeepSeek V4 Flash provider via NVIDIA NIM (OpenAI-compatible API).

Uses the openai SDK pointed at NVIDIA's inference endpoint so no additional
SDK is required beyond what is already standard in the Python ecosystem.
"""

import asyncio
import logging
import os
from typing import AsyncIterator, List, Dict, Any, Optional

import httpx
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_DEFAULT_MAX_RETRIES = 2       # reduced for MVP — fail fast on sustained 429
_DEFAULT_INITIAL_DELAY = 5.0
_DEFAULT_BACKOFF_FACTOR = 2.0
_DEFAULT_TIMEOUT = 120.0


class DeepSeekProvider(BaseLLMProvider):
    """LLM provider backed by DeepSeek V4 Flash on NVIDIA NIM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = (
            base_url
            or os.environ.get("DEEPSEEK_BASE_URL", "https://integrate.api.nvidia.com/v1")
        ).rstrip("/")
        self.model = model or os.environ.get(
            "DEEPSEEK_MODEL", "deepseek-ai/deepseek-v4-flash"
        )
        self.max_retries = max_retries
        self.timeout = timeout

        if not self.api_key:
            logger.warning(
                "DEEPSEEK_API_KEY is not set — requests to NVIDIA NIM will be rejected."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        prompt: str,
        system_instruction: Optional[str],
        history: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, str]]:
        """Assemble the OpenAI-style messages list."""
        messages: List[Dict[str, str]] = []

        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        if history:
            for turn in history:
                role = turn.get("role", "user")
                # Normalise 'model' role (Gemini convention) → 'assistant'
                if role == "model":
                    role = "assistant"
                content = turn.get("content", turn.get("parts", [""])[0] if isinstance(turn.get("parts"), list) else "")
                if content:
                    messages.append({"role": role, "content": str(content)})

        messages.append({"role": "user", "content": prompt})
        return messages

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _post_with_retry(
        self, client: httpx.AsyncClient, payload: Dict[str, Any]
    ) -> httpx.Response:
        """POST /chat/completions with exponential backoff."""
        url = f"{self.base_url}/chat/completions"
        delay = _DEFAULT_INITIAL_DELAY
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if response.status_code in _RETRY_STATUS_CODES and attempt < self.max_retries - 1:
                    logger.warning(
                        "DeepSeek NIM returned %s (attempt %d/%d). Retrying in %.1fs…",
                        response.status_code,
                        attempt + 1,
                        self.max_retries,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= _DEFAULT_BACKOFF_FACTOR
                    continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "DeepSeek NIM connection error (attempt %d/%d): %s. Retrying in %.1fs…",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= _DEFAULT_BACKOFF_FACTOR
                    continue
                raise

        raise last_exc or RuntimeError("Max retries exceeded for DeepSeek NIM request.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        response_mime_type: Optional[str] = None,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        messages = self._build_messages(prompt, system_instruction, history)

        # When JSON output is requested, ask the model to return valid JSON
        if response_mime_type == "application/json":
            if system_instruction:
                messages[0]["content"] += "\nYou MUST respond with valid JSON only. No markdown fences, no explanatory text outside the JSON object."
            else:
                messages.insert(0, {
                    "role": "system",
                    "content": "You MUST respond with valid JSON only. No markdown fences, no explanatory text outside the JSON object."
                })

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await self._post_with_retry(client, payload)

        data = response.json()
        text = data["choices"][0]["message"]["content"]

        # Strip markdown code fences that some models add around JSON
        if response_mime_type == "application/json":
            text = _strip_json_fences(text)

        return text

    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream token-by-token output via SSE."""
        messages = self._build_messages(prompt, system_instruction, history)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        url = f"{self.base_url}/chat/completions"
        delay = _DEFAULT_INITIAL_DELAY

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST", url, json=payload, headers=self._headers()
                    ) as response:
                        if response.status_code in _RETRY_STATUS_CODES and attempt < self.max_retries - 1:
                            logger.warning(
                                "DeepSeek stream returned %s. Retrying in %.1fs…",
                                response.status_code,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            delay *= _DEFAULT_BACKOFF_FACTOR
                            continue
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            raw = line[len("data:"):].strip()
                            if raw == "[DONE]":
                                return
                            try:
                                import json
                                chunk = json.loads(raw)
                                delta = chunk["choices"][0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    yield text
                            except Exception:
                                continue
                return  # success — exit retry loop
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                if attempt < self.max_retries - 1:
                    logger.warning("DeepSeek stream error: %s. Retrying…", exc)
                    await asyncio.sleep(delay)
                    delay *= _DEFAULT_BACKOFF_FACTOR
                    continue
                raise


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences that models sometimes wrap around JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (```json or ```) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        elif lines[0].strip().startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines).strip()
    return text
