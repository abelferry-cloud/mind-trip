# app/api/monitor.py
"""监控 API - 健康检查和指标。"""
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.services.metrics_service import get_metrics_service
from app.memory.long_term import get_long_term_memory
import aiosqlite

router = APIRouter(prefix="/api", tags=["monitor"])

@router.get("/health")
async def health():
    """健康检查端点。"""
    from app.services.model_router import get_model_router
    from app.config import get_settings
    settings = get_settings()
    router_instance = get_model_router()
    llm_primary_available = router_instance.is_primary_available()
    llm_available = llm_primary_available

    try:
        async with aiosqlite.connect(settings.database_url) as db:
            await db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if llm_available and db_status == "connected" else "degraded",
        "llm_available": llm_available,
        "llm_primary_available": llm_primary_available,
        "db_status": db_status
    }

@router.get("/metrics")
async def metrics():
    svc = get_metrics_service()
    return svc.get_summary()

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
