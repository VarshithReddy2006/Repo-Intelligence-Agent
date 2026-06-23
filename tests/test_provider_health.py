"""Unit tests for provider health checks.

All external SDK/HTTP calls are mocked — tests run fully offline.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm.base_provider import ProviderHealth
from services.llm.provider_errors import ProviderErrorType


# ===========================================================================
# GeminiProvider.health_check()
# ===========================================================================

class TestGeminiProviderHealthCheck:
    """Tests for GeminiProvider.health_check() — mocks genai.Client."""

    def _make_provider(self, api_key: str = "AIza-test-key", model: str = "gemini-2.5-flash"):
        with patch("services.llm.gemini_provider.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            from services.llm.gemini_provider import GeminiProvider
            provider = GeminiProvider.__new__(GeminiProvider)
            provider.api_key = api_key
            provider.model = model
            provider.client = mock_client
            return provider, mock_client

    @pytest.mark.anyio
    async def test_health_check_success(self):
        provider, mock_client = self._make_provider()
        # models.list() returns successfully
        mock_client.aio.models.list = AsyncMock(return_value=[])

        health = await provider.health_check()

        assert health.healthy is True
        assert health.authenticated is True
        assert health.provider == "gemini"
        assert health.model == "gemini-2.5-flash"
        assert health.error_message is None
        assert health.error_type is None
        assert health.latency_ms is not None
        assert health.latency_ms >= 0

    @pytest.mark.anyio
    async def test_health_check_missing_api_key(self):
        provider, _ = self._make_provider(api_key="")

        health = await provider.health_check()

        assert health.healthy is False
        assert health.authenticated is False
        assert health.error_type == ProviderErrorType.MISSING_CREDENTIAL.value
        assert "GEMINI_API_KEY" in health.recommendation
        assert health.latency_ms == 0.0

    @pytest.mark.anyio
    async def test_health_check_access_token_type_unsupported(self):
        """The exact failure mode that triggered this feature."""
        from tests.test_provider_errors import _mock_exc
        provider, mock_client = self._make_provider()

        exc = _mock_exc(
            "ClientError 401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED "
            "service: generativelanguage.googleapis.com",
            class_name="ClientError",
        )
        mock_client.aio.models.list = AsyncMock(side_effect=exc)

        health = await provider.health_check()

        assert health.healthy is False
        assert health.authenticated is False
        assert health.error_type == ProviderErrorType.INVALID_CREDENTIAL_TYPE.value
        assert "Google AI Studio" in health.recommendation
        assert "Developer API key" in health.recommendation

    @pytest.mark.anyio
    async def test_health_check_invalid_key_401(self):
        from tests.test_provider_errors import _mock_exc
        provider, mock_client = self._make_provider()

        exc = _mock_exc("ClientError 401 UNAUTHENTICATED", class_name="ClientError")
        mock_client.aio.models.list = AsyncMock(side_effect=exc)

        health = await provider.health_check()

        assert health.healthy is False
        assert health.authenticated is False
        assert health.error_type == ProviderErrorType.AUTHENTICATION_ERROR.value

    @pytest.mark.anyio
    async def test_health_check_rate_limited(self):
        from tests.test_provider_errors import _mock_exc
        provider, mock_client = self._make_provider()

        exc = _mock_exc("ClientError 429 RESOURCE_EXHAUSTED rate limit", class_name="ClientError")
        mock_client.aio.models.list = AsyncMock(side_effect=exc)

        health = await provider.health_check()

        assert health.healthy is False
        assert health.error_type == ProviderErrorType.RATE_LIMIT_ERROR.value
        # Rate limit is not an auth failure
        assert health.authenticated is True

    @pytest.mark.anyio
    async def test_health_check_timeout(self):
        provider, mock_client = self._make_provider()

        mock_client.aio.models.list = AsyncMock(side_effect=asyncio.TimeoutError())

        health = await provider.health_check()

        assert health.healthy is False
        assert health.error_type == ProviderErrorType.TIMEOUT.value

    @pytest.mark.anyio
    async def test_health_check_never_raises(self):
        """health_check() must always return ProviderHealth, never raise."""
        provider, mock_client = self._make_provider()
        mock_client.aio.models.list = AsyncMock(side_effect=RuntimeError("kaboom"))

        # Must not raise
        health = await provider.health_check()
        assert isinstance(health, ProviderHealth)
        assert health.healthy is False


# ===========================================================================
# DeepSeekProvider.health_check()
# ===========================================================================

class TestDeepSeekProviderHealthCheck:
    """Tests for DeepSeekProvider.health_check() — mocks httpx.AsyncClient."""

    def _make_provider(
        self,
        api_key: str = "nvapi-test",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model: str = "deepseek-ai/deepseek-v4-flash",
    ):
        from services.llm.deepseek_provider import DeepSeekProvider
        provider = DeepSeekProvider.__new__(DeepSeekProvider)
        provider.api_key = api_key
        provider.base_url = base_url.rstrip("/")
        provider.model = model
        provider.max_retries = 2
        provider.timeout = 120.0
        return provider

    @pytest.mark.anyio
    async def test_health_check_success(self):
        provider = self._make_provider()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("services.llm.deepseek_provider.httpx.AsyncClient", return_value=mock_client):
            health = await provider.health_check()

        assert health.healthy is True
        assert health.authenticated is True
        assert health.provider == "deepseek"
        assert health.error_type is None
        assert health.latency_ms is not None

    @pytest.mark.anyio
    async def test_health_check_missing_api_key(self):
        provider = self._make_provider(api_key="")

        health = await provider.health_check()

        assert health.healthy is False
        assert health.authenticated is False
        assert health.error_type == ProviderErrorType.MISSING_CREDENTIAL.value
        assert "DEEPSEEK_API_KEY" in health.recommendation
        assert health.latency_ms == 0.0

    @pytest.mark.anyio
    async def test_health_check_401_unauthorized(self):
        provider = self._make_provider()

        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        http_exc = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=http_exc)

        with patch("services.llm.deepseek_provider.httpx.AsyncClient", return_value=mock_client):
            health = await provider.health_check()

        assert health.healthy is False
        assert health.authenticated is False
        assert health.error_type == ProviderErrorType.AUTHENTICATION_ERROR.value

    @pytest.mark.anyio
    async def test_health_check_timeout(self):
        provider = self._make_provider()

        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with patch("services.llm.deepseek_provider.httpx.AsyncClient", return_value=mock_client):
            health = await provider.health_check()

        assert health.healthy is False
        assert health.error_type == ProviderErrorType.TIMEOUT.value

    @pytest.mark.anyio
    async def test_health_check_network_error(self):
        provider = self._make_provider()

        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with patch("services.llm.deepseek_provider.httpx.AsyncClient", return_value=mock_client):
            health = await provider.health_check()

        assert health.healthy is False
        assert health.error_type == ProviderErrorType.NETWORK_ERROR.value

    @pytest.mark.anyio
    async def test_health_check_never_raises(self):
        """health_check() must always return ProviderHealth, never raise."""
        provider = self._make_provider()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("kaboom"))

        with patch("services.llm.deepseek_provider.httpx.AsyncClient", return_value=mock_client):
            health = await provider.health_check()

        assert isinstance(health, ProviderHealth)
        assert health.healthy is False


# ===========================================================================
# ProviderHealth dataclass contract
# ===========================================================================

class TestProviderHealthDataclass:
    def test_healthy_instance(self):
        h = ProviderHealth(
            healthy=True,
            provider="gemini",
            model="gemini-2.5-flash",
            authenticated=True,
            latency_ms=234.5,
        )
        assert h.healthy is True
        assert h.error_message is None
        assert h.recommendation is None

    def test_unhealthy_instance(self):
        h = ProviderHealth(
            healthy=False,
            provider="gemini",
            model="gemini-2.5-flash",
            authenticated=False,
            latency_ms=10.0,
            error_message="API key is invalid.",
            error_type="authentication_error",
            recommendation="Regenerate your API key.",
        )
        assert h.healthy is False
        assert h.authenticated is False
        assert h.error_type == "authentication_error"
