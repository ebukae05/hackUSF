from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.adk.agents import Agent

from services.relieflink_agents.models import DisasterEvent


def build_disaster_event(state: str = "FL") -> dict[str, Any]:
    event = DisasterEvent(
        disaster_id=f"{state}-DEMO-001",
        disaster_type="hurricane",
        state=state,
        declared_date=datetime.now(timezone.utc).isoformat(),
        geographic_footprint=["12057", "12103"],
        severity=8.4,
        affected_population=13400,
        active_alerts=[{"event": "Hurricane Warning", "severity": "Extreme"}],
    )
    return {"disaster_event": event.to_dict()}


DisasterMonitor = Agent(
    name="DisasterMonitor",
    model="gemini-2.5-flash",
    description="Ingests FEMA and NOAA disaster context for the requested state.",
    instruction="Use the tool to create a structured DisasterEvent for the requested state. Return JSON only.",
    tools=[build_disaster_event],
    output_key="disaster_monitor_output",
)
