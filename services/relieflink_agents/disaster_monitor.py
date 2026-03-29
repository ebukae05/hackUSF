"""
DisasterMonitor Agent (B2) — CS-01.
Ingests FEMA disaster declarations and NOAA weather alerts, produces a DisasterEvent.
Strategy S3: Custom BaseAgent wrapping deterministic Python helpers.
Pattern P3: Private helper functions _fetch_fema / _fetch_noaa on the agent class.
Reference: docs/SYSTEM_DESIGN.md Section 1.3.B (B2), 1.3.E (CF-01)
"""
import logging
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from services.relieflink_agents._mock_models import DisasterEvent, DisasterType, NOAAAlert
from services.relieflink_agents.api_clients import get_disaster_declarations, get_active_alerts

logger = logging.getLogger(__name__)

_INCIDENT_TYPE_MAP = {
    "Hurricane": DisasterType.HURRICANE,
    "Flood": DisasterType.FLOOD,
    "Tornado": DisasterType.TORNADO,
    "Fire": DisasterType.WILDFIRE,
    "Severe Storm(s)": DisasterType.SEVERE_STORM,
    "Coastal Storm": DisasterType.COASTAL_STORM,
    "Tropical Storm": DisasterType.TROPICAL_STORM,
}

_SEVERITY_MAP = {
    DisasterType.HURRICANE: 9.0,
    DisasterType.FLOOD: 7.0,
    DisasterType.TORNADO: 8.0,
    DisasterType.WILDFIRE: 7.5,
    DisasterType.SEVERE_STORM: 6.0,
    DisasterType.COASTAL_STORM: 6.5,
    DisasterType.TROPICAL_STORM: 7.0,
    DisasterType.OTHER: 5.0,
}

_NOAA_SEVERITY_BONUS = {"Extreme": 1.0, "Severe": 0.5, "Moderate": 0.0, "Minor": -0.5}


class DisasterMonitorAgent(BaseAgent):
    """
    ADK BaseAgent that ingests FEMA + NOAA data and produces a DisasterEvent
    stored in session state under output_key='disaster_event'.
    No LLM inference — fully deterministic execution.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, state: str = "FL", **kwargs):
        super().__init__(name="DisasterMonitorAgent", **kwargs)
        self._state = state

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        declarations = self._fetch_fema(self._state)
        alerts = self._fetch_noaa(self._state)

        fallback_used = not declarations or declarations[0].get("_fallback", False)
        noaa_fallback = len(alerts) == 0

        if declarations:
            decl = declarations[0]
            disaster_id = str(decl.get("disasterNumber", "UNKNOWN"))
            incident_type_str = decl.get("incidentType", "")
            disaster_type = _INCIDENT_TYPE_MAP.get(incident_type_str, DisasterType.OTHER)
            declared_date = decl.get("declarationDate", "")
            geographic_footprint = [
                d.get("placeCode", "") for d in declarations if d.get("placeCode")
            ]
            affected_population = len(geographic_footprint) * 50000
        else:
            disaster_id = "FALLBACK-001"
            disaster_type = DisasterType.HURRICANE
            declared_date = ""
            geographic_footprint = []
            affected_population = 0

        base_severity = _SEVERITY_MAP.get(disaster_type, 5.0)
        noaa_bonus = max(
            (_NOAA_SEVERITY_BONUS.get(a.get("severity", ""), 0.0) for a in alerts),
            default=0.0,
        )
        severity = min(10.0, base_severity + noaa_bonus)

        active_alerts = [
            NOAAAlert(
                id=a.get("id", ""),
                event=a.get("event", ""),
                severity=a.get("severity", "Unknown"),
                headline=a.get("headline", ""),
                area_desc=a.get("areaDesc", ""),
                urgency=a.get("urgency", "Unknown"),
                onset=a.get("onset"),
                expires=a.get("expires"),
            )
            for a in alerts
        ]

        event = DisasterEvent(
            disaster_id=disaster_id,
            disaster_type=disaster_type,
            state=self._state,
            declared_date=declared_date,
            geographic_footprint=geographic_footprint,
            severity=severity,
            affected_population=affected_population,
            active_alerts=active_alerts,
        )

        output = {
            "disaster_id": event.disaster_id,
            "disaster_type": event.disaster_type.value,
            "state": event.state,
            "declared_date": event.declared_date,
            "geographic_footprint": event.geographic_footprint,
            "severity": event.severity,
            "affected_population": event.affected_population,
            "active_alerts": [
                {
                    "id": a.id, "event": a.event, "severity": a.severity,
                    "headline": a.headline, "area_desc": a.area_desc, "urgency": a.urgency,
                }
                for a in event.active_alerts
            ],
            "fallback_used": fallback_used,
            "noaa_fallback": noaa_fallback,
        }

        ctx.session.state["disaster_event"] = output
        logger.info(
            "DisasterMonitor: ingested disaster_id=%s severity=%.1f alerts=%d fallback=%s",
            event.disaster_id, event.severity, len(event.active_alerts), fallback_used,
        )

        if False:
            yield

    def _fetch_fema(self, state: str) -> list[dict]:
        """Fetch FEMA disaster declarations via FT-02 client."""
        return get_disaster_declarations(state)

    def _fetch_noaa(self, state: str) -> list[dict]:
        """Fetch NOAA active alerts via FT-02 client."""
        return get_active_alerts(state)
