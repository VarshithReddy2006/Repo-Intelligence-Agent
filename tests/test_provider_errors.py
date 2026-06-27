"""Unit tests for the provider error classification system.

Tests every error category for both Gemini and DeepSeek classifiers.
All external API calls are mocked — these tests run offline.
"""

from services.llm.provider_errors import (
    ProviderErrorType,
    classify_gemini_error,
    classify_deepseek_error,
)


# ---------------------------------------------------------------------------
# Helper: build a mock exception with a given string representation
# ---------------------------------------------------------------------------


class _MockException(Exception):
    """Stand-in for SDK exceptions that carry status codes in their message."""

    pass


def _mock_exc(message: str, class_name: str = "_MockException") -> Exception:
    """Create a fresh exception class with the given name to avoid shared state."""
    exc_cls = type(class_name, (Exception,), {})
    return exc_cls(message)


class _MockHTTPException(Exception):
    """Stand-in for httpx.HTTPStatusError with a .response attribute."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.response = type("R", (), {"status_code": status_code})()


# ===========================================================================
# Gemini error classification
# ===========================================================================


class TestClassifyGeminiError:
    def test_missing_credential(self):
        exc = _mock_exc("api_key is not set")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.MISSING_CREDENTIAL
        assert "GEMINI_API_KEY" in result.recommendation

    def test_access_token_type_unsupported(self):
        """The specific error that triggered this entire effort."""
        exc = _mock_exc(
            "ClientError 401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED "
            "service: generativelanguage.googleapis.com "
            "method: GenerativeService.StreamGenerateContent",
            class_name="ClientError",
        )
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.INVALID_CREDENTIAL_TYPE
        assert "Google AI Studio" in result.recommendation
        assert "Developer API key" in result.recommendation

    def test_generic_401_unauthenticated(self):
        exc = _mock_exc("ClientError 401 UNAUTHENTICATED", class_name="ClientError")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.AUTHENTICATION_ERROR

    def test_403_permission_denied(self):
        exc = _mock_exc("ClientError 403 PERMISSION_DENIED", class_name="ClientError")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.AUTHENTICATION_ERROR

    def test_429_rate_limit(self):
        exc = _mock_exc(
            "ClientError 429 RESOURCE_EXHAUSTED rate limit", class_name="ClientError"
        )
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.RATE_LIMIT_ERROR

    def test_429_quota_exceeded(self):
        exc = _mock_exc(
            "ClientError 429 RESOURCE_EXHAUSTED quota exceeded",
            class_name="ClientError",
        )
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.QUOTA_EXCEEDED

    def test_503_service_unavailable(self):
        exc = _mock_exc("ClientError 503 unavailable", class_name="ClientError")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.NETWORK_ERROR

    def test_timeout(self):
        exc = _mock_exc("request timed out", class_name="TimeoutError")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.TIMEOUT

    def test_network_error(self):
        exc = _mock_exc("connection refused", class_name="ConnectError")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.NETWORK_ERROR

    def test_unknown_error_defaults_safely(self):
        exc = _mock_exc("something completely unexpected happened")
        result = classify_gemini_error(exc)
        assert result.error_type == ProviderErrorType.UNKNOWN_PROVIDER_ERROR
        assert result.provider_name == "gemini"

    def test_provider_name_preserved(self):
        exc = _mock_exc("any error")
        result = classify_gemini_error(exc, provider_name="gemini-custom")
        assert result.provider_name == "gemini-custom"

    def test_original_exception_attached(self):
        exc = _mock_exc("something")
        result = classify_gemini_error(exc)
        assert result.original_exception is exc

    def test_message_never_exposes_api_key(self):
        """Ensure the classified message never leaks credential values."""
        exc = _mock_exc(
            "401 api_key=AIzaSyFAKEKEY123 is invalid", class_name="ClientError"
        )
        result = classify_gemini_error(exc)
        assert "AIzaSyFAKEKEY123" not in result.message
        assert "AIzaSyFAKEKEY123" not in result.recommendation


# ===========================================================================
# DeepSeek / NVIDIA NIM error classification
# ===========================================================================


class TestClassifyDeepSeekError:
    def test_missing_credential(self):
        exc = _mock_exc("api_key is not set")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.MISSING_CREDENTIAL
        assert "DEEPSEEK_API_KEY" in result.recommendation

    def test_401_via_response_attribute(self):
        exc = _MockHTTPException("401 Unauthorized", status_code=401)
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.AUTHENTICATION_ERROR

    def test_403_via_response_attribute(self):
        exc = _MockHTTPException("403 Forbidden", status_code=403)
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.AUTHENTICATION_ERROR

    def test_429_via_response_attribute(self):
        exc = _MockHTTPException("429 Too Many Requests", status_code=429)
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.RATE_LIMIT_ERROR

    def test_401_via_string(self):
        exc = _mock_exc("401 unauthorized")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.AUTHENTICATION_ERROR

    def test_rate_limit_via_string(self):
        exc = _mock_exc("too many requests rate limit")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.RATE_LIMIT_ERROR

    def test_timeout(self):
        exc = _mock_exc("timed out", class_name="TimeoutException")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.TIMEOUT

    def test_network_error(self):
        exc = _mock_exc("could not connect", class_name="ConnectError")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.NETWORK_ERROR

    def test_unknown_error_defaults_safely(self):
        exc = _mock_exc("something completely unexpected happened XYZ")
        result = classify_deepseek_error(exc)
        assert result.error_type == ProviderErrorType.UNKNOWN_PROVIDER_ERROR

    def test_provider_name_preserved(self):
        exc = _mock_exc("any error")
        result = classify_deepseek_error(exc, provider_name="deepseek-v4")
        assert result.provider_name == "deepseek-v4"

    def test_original_exception_attached(self):
        exc = _mock_exc("something")
        result = classify_deepseek_error(exc)
        assert result.original_exception is exc


# ===========================================================================
# ProviderErrorType — enum contract
# ===========================================================================


class TestProviderErrorType:
    """Ensure enum values are stable strings (used in logs and API responses)."""

    def test_value_strings(self):
        assert ProviderErrorType.MISSING_CREDENTIAL.value == "missing_credential"
        assert ProviderErrorType.AUTHENTICATION_ERROR.value == "authentication_error"
        assert (
            ProviderErrorType.INVALID_CREDENTIAL_TYPE.value == "invalid_credential_type"
        )
        assert ProviderErrorType.RATE_LIMIT_ERROR.value == "rate_limit_error"
        assert ProviderErrorType.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert ProviderErrorType.TIMEOUT.value == "timeout"
        assert ProviderErrorType.NETWORK_ERROR.value == "network_error"
        assert ProviderErrorType.CONFIGURATION_ERROR.value == "configuration_error"
        assert (
            ProviderErrorType.UNKNOWN_PROVIDER_ERROR.value == "unknown_provider_error"
        )
