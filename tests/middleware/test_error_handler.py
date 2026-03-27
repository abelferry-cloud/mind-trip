# tests/middleware/test_error_handler.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.error_handler import ErrorHandlerMiddleware, AgentError, AllAgentsFailedError

def test_agent_error_recoverable():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    @app.get("/test")
    def raise_recoverable():
        raise AgentError("Attractions Agent", "timeout", recoverable=True)

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "fallback" in resp.json()

def test_all_agents_failed_returns_fallback():
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    @app.get("/test")
    def raise_all_failed():
        raise AllAgentsFailedError()

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert "fallback" in resp.json()
