# app/api/preference.py
"""偏好 API - 管理用户偏好。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.agents.preference import PreferenceAgent

router = APIRouter(prefix="/api", tags=["preference"])

class PreferenceResponse(BaseModel):
    user_id: str
    preferences: dict
    history_trips: list

class PreferenceUpdate(BaseModel):
    key: str
    value: Any

_agent = PreferenceAgent()

@router.get("/preference/{user_id}", response_model=PreferenceResponse)
async def get_preference(user_id: str):
    prefs = await _agent.get_preference(user_id)
    return PreferenceResponse(user_id=user_id, preferences=prefs, history_trips=[])

@router.put("/preference/{user_id}")
async def update_preference(user_id: str, body: PreferenceUpdate):
    result = await _agent.update_preference(user_id, body.key, body.value)
    return result
