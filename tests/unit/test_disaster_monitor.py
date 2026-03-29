"""Unit tests for DisasterMonitorAgent (P-04)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.relieflink_agents.models import DisasterEvent, DisasterType, NOAAAlert
from services.relieflink_agents.disaster_monitor import DisasterMonitorAgent


SAMPLE_DECLARATIONS = [
    {
        "disasterNumber": 4844,
        "declarationTitle": "HURRICANE MILTON",
        "incidentType": "Hurricane",
        "state": "FL",
        "declarationDate": "2024-10-11T00:00:00.000Z",
        "placeCode": "12057",
        # FEMA program flags — all active for a major hurricane
        "iaProgramDeclared": True,
        "paProgramDeclared": True,
        "ihProgramDeclared": True,
        "hmProgramDeclared": True,
    },
    {
        "disasterNumber": 4844,
        "declarationTitle": "HURRICANE MILTON",
        "incidentType": "Hurricane",
        "state": "FL",
        "declarationDate": "2024-10-11T00:00:00.000Z",
        "placeCode": "12103",
        "iaProgramDeclared": True,
        "paProgramDeclared": True,
        "ihProgramDeclared": True,
        "hmProgramDeclared": True,
    },
]

SAMPLE_ALERTS = [
    {
        "id": "alert-1",
        "event": "Hurricane Warning",
        "severity": "Extreme",
        "headline": "Hurricane Warning issued for Tampa Bay",
        "areaDesc": "Hillsborough County, FL",
        "urgency": "Immediate",
        "onset": "2026-03-29T08:00:00-04:00",
        "expires": "2026-03-30T08:00:00-04:00",
    }
]


def make_ctx(state_dict=None):
    ctx = MagicMock()
    ctx.session.state = state_dict if state_dict is not None else {}
    return ctx


def run_agent(agent, ctx):
    """Run _run_async_impl and exhaust the async generator."""
    async def _run():
        async for _ in agent._run_async_impl(ctx):
            pass
    asyncio.run(_run())


class TestDisasterMonitorAgent:
    def test_is_base_agent_subclass(self):
        from google.adk.agents.base_agent import BaseAgent
        agent = DisasterMonitorAgent(state="FL")
        assert isinstance(agent, BaseAgent)

    def test_happy_path_writes_disaster_event_to_session_state(self):
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=SAMPLE_DECLARATIONS), \
             patch.object(agent, "_fetch_noaa", return_value=SAMPLE_ALERTS):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        assert result["disaster_id"] == "4844"
        assert result["disaster_type"] == "hurricane"
        assert result["state"] == "FL"
        assert "12057" in result["geographic_footprint"]
        assert result["severity"] > 0
        assert len(result["active_alerts"]) == 1

    def test_fema_fallback_sets_fallback_used(self):
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=[]), \
             patch.object(agent, "_fetch_noaa", return_value=[]):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        assert result["fallback_used"] is True
        assert result["disaster_id"] == "FALLBACK-001"

    def test_noaa_fallback_sets_noaa_fallback(self):
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=SAMPLE_DECLARATIONS), \
             patch.object(agent, "_fetch_noaa", return_value=[]):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        assert result["noaa_fallback"] is True
        assert result["active_alerts"] == []

    def test_fetch_fema_calls_api_client(self):
        agent = DisasterMonitorAgent(state="FL")
        with patch(
            "services.relieflink_agents.disaster_monitor.get_disaster_declarations",
            return_value=SAMPLE_DECLARATIONS,
        ) as mock_fema:
            result = agent._fetch_fema("FL")
        mock_fema.assert_called_once_with("FL")
        assert result == SAMPLE_DECLARATIONS

    def test_fetch_noaa_calls_api_client(self):
        agent = DisasterMonitorAgent(state="FL")
        with patch(
            "services.relieflink_agents.disaster_monitor.get_active_alerts",
            return_value=SAMPLE_ALERTS,
        ) as mock_noaa:
            result = agent._fetch_noaa("FL")
        mock_noaa.assert_called_once_with("FL")
        assert result == SAMPLE_ALERTS

    def test_severity_boosted_by_extreme_alert(self):
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=SAMPLE_DECLARATIONS), \
             patch.object(agent, "_fetch_noaa", return_value=SAMPLE_ALERTS):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        assert result["severity"] == 10.0  # 9.0 (hurricane) + 1.0 (extreme) = 10.0

    def test_session_state_contract_has_all_cf01_fields(self):
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=SAMPLE_DECLARATIONS), \
             patch.object(agent, "_fetch_noaa", return_value=SAMPLE_ALERTS):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        required_fields = [
            "disaster_id", "disaster_type", "state", "declared_date",
            "geographic_footprint", "severity", "affected_population",
            "active_alerts", "fallback_used", "noaa_fallback",
        ]
        for field in required_fields:
            assert field in result, f"Missing CF-01 field: {field}"

    def test_both_fema_and_noaa_fail_simultaneously(self):
        """Issue 2 fix: both APIs fail → fallback_used=True, noaa_fallback=True, safe output."""
        agent = DisasterMonitorAgent(state="FL")
        ctx = make_ctx()
        with patch.object(agent, "_fetch_fema", return_value=[]), \
             patch.object(agent, "_fetch_noaa", return_value=[]):
            run_agent(agent, ctx)
        result = ctx.session.state["disaster_event"]
        assert result["fallback_used"] is True
        assert result["noaa_fallback"] is True
        assert result["active_alerts"] == []
        assert result["disaster_id"] == "FALLBACK-001"
        assert result["severity"] > 0
