# tests/middleware/test_tracing.py
import pytest
from unittest.mock import MagicMock
from app.middleware.tracing import TracingMiddleware

def test_trace_id_generated():
    mock_app = MagicMock()
    middleware = TracingMiddleware(mock_app)
    assert middleware.app is mock_app

def test_trace_id_propagates():
    from starlette.testclient import TestClient
    from fastapi import FastAPI
    from app.middleware.tracing import TracingMiddleware

    app = FastAPI()
    app.add_middleware(TracingMiddleware)

    @app.get("/test")
    def test_route():
        from app.middleware.tracing import get_trace_id
        return {"trace_id": get_trace_id()}

    client = TestClient(app)
    resp = client.get("/test")
    assert "trace_id" in resp.json()