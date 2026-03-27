# tests/services/test_model_router.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.model_router import ModelRouter, get_model_router

@pytest.mark.asyncio
async def test_fallback_on_timeout():
    router = get_model_router()
    with patch.object(router, "_call_openai", side_effect=TimeoutError()):
        with patch.object(router, "_call_claude", return_value="Claude response"):
            result = await router.call("test prompt")
            assert result == "Claude response"

@pytest.mark.asyncio
async def test_fallback_on_429():
    router = get_model_router()
    with patch.object(router, "_call_openai", side_effect=Exception("429 rate limit")):
        with patch.object(router, "_call_claude", return_value="Claude response"):
            result = await router.call("test prompt")
            assert result == "Claude response"

def test_check_primary_available():
    router = get_model_router()
    assert router.is_primary_available() is True
