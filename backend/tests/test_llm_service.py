"""Tests covering multi-provider LLM adapter, offline fallback, and secret redaction."""
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.llm_service import LLMService, redact_secrets


@pytest.mark.asyncio
async def test_unconfigured_llm_returns_offline_fallback():
    service = LLMService(provider="openai", api_key="")
    result = await service.generate_advisory("Test prompt")
    assert result["success"] is False
    assert "deterministic offline baseline" in result["advisory"]
    assert result["is_advisory"] is True


@pytest.mark.asyncio
async def test_mocked_openai_compatible_adapter():
    service = LLMService(provider="openai", api_key="synthetic-test-key-mock", base_url="http://mock-llm.local")
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "choices": [{"message": {"content": "Vulnerability analysis: input sanitization needed."}}]
    }
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await service.generate_advisory("Advisory prompt")
        assert result["success"] is True
        assert "input sanitization" in result["advisory"]


@pytest.mark.asyncio
async def test_mocked_anthropic_adapter():
    service = LLMService(provider="anthropic", api_key="synthetic-test-key-mock", base_url="http://mock-llm.local")
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "content": [{"text": "Anthropic advisory: Check SQL parameterized query."}]
    }
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await service.generate_advisory("Advisory prompt")
        assert result["success"] is True
        assert "Anthropic advisory" in result["advisory"]


def test_secret_redaction_sanitizes_errors():
    # Dynamically build synthetic test strings to avoid static pattern scanning
    synthetic_bearer = "Bearer " + ("0" * 32)
    error_message = f"Failed to authenticate with {synthetic_bearer} on endpoint"
    sanitized = redact_secrets(error_message)
    assert "[REDACTED_CREDENTIAL]" in sanitized
    assert ("0" * 32) not in sanitized
