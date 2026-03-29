from __future__ import annotations

from typing import Any

from google.adk.agents import Agent

from services.relieflink_agents.models import Community, Need


def build_needs(disaster_footprint: list[str] | None = None, disaster_severity: float = 8.4, state: str = "FL") -> dict[str, Any]:
    communities = [
        Community("12057010100", "12057", state, 5200, 0.91, {"socioeconomic": 0.82, "household": 0.88, "minority": 0.94, "housing": 0.86}),
        Community("12103026403", "12103", state, 3900, 0.74, {"socioeconomic": 0.68, "household": 0.71, "minority": 0.76, "housing": 0.72}),
        Community("12057011000", "12057", state, 4300, 0.63, {"socioeconomic": 0.61, "household": 0.58, "minority": 0.65, "housing": 0.59}),
    ]
    needs = [
        Need("need-shelter-1", "12057010100", "shelter", 8.8, 180, 0),
        Need("need-medical-1", "12103026403", "medical", 8.1, 3, 0),
        Need("need-supplies-1", "12057011000", "supplies", 6.9, 90, 0),
    ]
    return {
        "communities": [community.to_dict() for community in communities],
        "needs": [need.to_dict() for need in needs],
        "needs_summary": {
            "by_type": {"shelter": 180, "medical": 3, "supplies": 90},
            "by_severity": {"critical": 2, "high": 1, "moderate": 0},
        },
    }


NeedMapper = Agent(
    name="NeedMapper",
    model="gemini-2.5-flash",
    description="Maps vulnerable communities to quantified disaster needs.",
    instruction="Use the tool to map communities and needs from the disaster footprint. Return JSON only.",
    tools=[build_needs],
    output_key="need_mapper_output",
)
