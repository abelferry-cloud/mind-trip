# app/api/plan.py
"""Plan API - retrieve saved plans."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["plan"])

# In-memory plan store (for demo; replace with Redis/DB in production)
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
    """Called by chat endpoint after plan is generated."""
    _plan_store[plan_id] = plan_data
