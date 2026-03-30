# app/services/model/__init__.py
"""Model services - 模型路由和调用。"""

from app.services.model.model_router import (
    ModelRouter,
    ModelName,
    get_model_router,
)

__all__ = [
    "ModelRouter",
    "ModelName",
    "get_model_router",
]
