# app/api/plan.py
"""方案 API - 获取已保存的方案。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["plan"])

# 内存方案存储（演示用；生产环境请替换为 Redis/数据库）
_plan_store: dict = {}

class PlanResponse(BaseModel):
    plan_id: str
    city: str
    days: int
    daily_routes: list
    attractions: list
    food: list
    hotels: list
    budget_summary: dict
    health_alerts: list
    preference_compliance: list

@router.get("/plan/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    plan = _plan_store.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

def save_plan(plan_id: str, plan_data: dict):
    """由聊天端点在生成方案后调用。"""
    _plan_store[plan_id] = plan_data
