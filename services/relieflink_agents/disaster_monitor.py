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

from services.relieflink_agents.models import DisasterEvent, DisasterType, NOAAAlert
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

# Fallback severity by disaster type — used only when FEMA program flags are unavailable
_SEVERITY_MAP = {
    DisasterType.HURRICANE: 7.0,
    DisasterType.FLOOD: 6.0,
    DisasterType.TORNADO: 6.5,
    DisasterType.WILDFIRE: 6.0,
    DisasterType.SEVERE_STORM: 5.0,
    DisasterType.COASTAL_STORM: 5.5,
    DisasterType.TROPICAL_STORM: 5.5,
    DisasterType.OTHER: 4.0,
}

_NOAA_SEVERITY_BONUS = {"Extreme": 1.0, "Severe": 0.5, "Moderate": 0.0, "Minor": -0.5}


def _severity_from_fema_programs(declaration: dict, disaster_type: DisasterType) -> float:
    """
    Calculate severity from FEMA program declarations — more accurate than hardcoding
    by disaster type because FEMA only activates these programs when real damage justifies it.

    iaProgramDeclared: Individual Assistance — people lost homes, need direct aid (+3.0)
    paProgramDeclared: Public Assistance — infrastructure destroyed (+2.5)
    ihProgramDeclared: Individual + Household — personal property destroyed (+2.5)
    hmProgramDeclared: Hazard Mitigation — serious enough for long-term prevention (+1.0)

    A small storm with only hmProgramDeclared → ~1.0
    Hurricane Milton with all 4 activated → 9.0 (then NOAA pushes to 10.0)
    """
    ia = declaration.get("iaProgramDeclared", False)
    pa = declaration.get("paProgramDeclared", False)
    ih = declaration.get("ihProgramDeclared", False)
    hm = declaration.get("hmProgramDeclared", False)

    # If no programs declared, fall back to disaster type map
    if not any([ia, pa, ih, hm]):
        logger.info(
            "DisasterMonitor: no FEMA program flags found — using disaster type fallback severity"
        )
        return _SEVERITY_MAP.get(disaster_type, 4.0)

    severity = 0.0
    if ia: severity += 3.0   # people need immediate individual help
    if pa: severity += 2.5   # public infrastructure destroyed
    if ih: severity += 2.5   # household property destroyed
    if hm: severity += 1.0   # serious enough for hazard mitigation funding

    logger.info(
        "DisasterMonitor: FEMA programs IA=%s PA=%s IH=%s HM=%s → base severity %.1f",
        ia, pa, ih, hm, severity
    )
    return min(severity, 9.0)  # cap before NOAA bonus


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
            # Filter to valid Census FIPS county codes only (5-digit, state prefix "12" for FL).
            # FEMA placeCode also includes statewide/special codes (e.g. 99001) that don't
            # match Census FIPS and would produce no SVI results downstream.
            _state_fips = {"FL": "12"}.get(self._state, "")
            raw_codes = [d.get("placeCode", "") for d in declarations if d.get("placeCode")]
            geographic_footprint = [
                c for c in raw_codes
                if len(c) == 5 and (_state_fips == "" or c.startswith(_state_fips))
            ]
            # If no valid FIPS codes found, fall back to Tampa Bay demo footprint
            if not geographic_footprint:
                logger.warning(
                    "DisasterMonitor: no valid Census FIPS county codes in FEMA placeCode "
                    "fields (%s). Using Tampa Bay demo footprint.", raw_codes[:5]
                )
                geographic_footprint = ["12057", "12103", "12081", "12101"]
            affected_population = len(geographic_footprint) * 50000
        else:
            disaster_id = "FALLBACK-001"
            disaster_type = DisasterType.HURRICANE
            declared_date = ""
            geographic_footprint = []
            affected_population = 0

        # Severity from FEMA program declarations (live data-driven, not hardcoded)
        # Falls back to disaster type map if no programs declared
        decl_for_severity = declarations[0] if declarations else {}
        base_severity = _severity_from_fema_programs(decl_for_severity, disaster_type)
        noaa_bonus = max(
            (_NOAA_SEVERITY_BONUS.get(a.get("severity", ""), 0.0) for a in alerts),
            default=0.0,
        )
        severity = min(10.0, base_severity + noaa_bonus)

        active_alerts = [
            NOAAAlert(
                alert_id=a.get("id", ""),
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
                    "alert_id": a.alert_id, "event": a.event, "severity": a.severity,
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
