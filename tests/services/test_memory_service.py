import pytest
from unittest.mock import AsyncMock, patch
from app.services.memory_service import MemoryService, get_memory_service

def test_write_only_from_preference_agent():
    """Verify only Preference Agent can write; other agents get read-only."""
    svc = get_memory_service()
    # Preference Agent role can write
    assert svc.can_write("PreferenceAgent") is True
    # Other agents are read-only
    assert svc.can_write("AttractionsAgent") is False
    assert svc.can_write("RouteAgent") is False

def test_read_allowed_for_all():
    svc = get_memory_service()
    assert svc.can_read("AttractionsAgent") is True
    assert svc.can_read("PlanningAgent") is True