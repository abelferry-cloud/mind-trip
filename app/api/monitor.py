# app/api/monitor.py
"""监控 API - 健康检查和指标。"""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.services.metrics_service import get_metrics_service

router = APIRouter(prefix="/api", tags=["monitor"])

@router.get("/health")
async def health():
    """健康检查端点。

    Checks:
    - LLM availability (via model router)
    - Memory subsystem: workspace and memory/ directories exist
    """
    from app.services.model_router import get_model_router
    router_instance = get_model_router()
    llm_primary_available = router_instance.is_primary_available()
    llm_available = llm_primary_available

    # Check Markdown memory directories exist
    base_dir = Path(__file__).parent.parent
    workspace_exists = (base_dir / "workspace").is_dir()
    memory_dir_exists = (base_dir / "workspace" / "memory").is_dir()

    memory_status = "ok" if (workspace_exists and memory_dir_exists) else "missing"

    overall = "healthy" if (llm_available and memory_status == "ok") else "degraded"

    return {
        "status": overall,
        "llm_available": llm_available,
        "llm_primary_available": llm_primary_available,
        "memory_status": memory_status,
    }

@router.get("/metrics")
async def metrics():
    svc = get_metrics_service()
    return svc.get_summary()

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
