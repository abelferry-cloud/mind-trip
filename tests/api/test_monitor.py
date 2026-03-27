# tests/api/test_monitor.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.api.monitor import router as monitor_router
from fastapi import FastAPI
from unittest.mock import patch, MagicMock

# Create test app
monitor_app = FastAPI()
monitor_app.include_router(monitor_router)

@pytest.mark.asyncio
async def test_health_returns_llm_fields():
    with patch("app.services.model_router.get_model_router") as mock_get_router:
        mock_router_instance = MagicMock()
        mock_router_instance.is_primary_available.return_value = True
        mock_get_router.return_value = mock_router_instance
        with patch("app.api.monitor.aiosqlite.connect") as mock_db:
            mock_db.return_value.__aenter__.return_value.execute = MagicMock()
            transport = ASGITransport(app=monitor_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/health")
                assert resp.status_code == 200
                data = resp.json()
                assert "llm_available" in data
                assert "llm_primary_available" in data
                assert "db_status" in data

@pytest.mark.asyncio
async def test_metrics_endpoint():
    with patch("app.api.monitor.get_metrics_service") as mock_get_svc:
        mock_svc_instance = MagicMock()
        mock_svc_instance.get_summary.return_value = {
            "qps": 10,
            "latency_p50_ms": 100,
            "latency_p99_ms": 500,
            "error_rate": 0.01
        }
        mock_get_svc.return_value = mock_svc_instance
        transport = ASGITransport(app=monitor_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/metrics")
            assert resp.status_code == 200
            data = resp.json()
            assert "qps" in data
