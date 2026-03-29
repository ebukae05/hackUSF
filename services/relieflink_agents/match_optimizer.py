from __future__ import annotations

from typing import Any
from uuid import uuid4

from google.adk.agents import Agent

from services.relieflink_agents.models import Match


def optimize_matches(
    resources: list[dict[str, Any]],
    communities: list[dict[str, Any]],
    needs: list[dict[str, Any]],
    previous_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    community_index = {community["fips_tract"]: community for community in communities}
    ranked_needs = sorted(
        needs,
        key=lambda need: community_index[need["community_fips_tract"]]["vulnerability_index"] * 0.6 + (need["severity"] / 10.0) * 0.4,
        reverse=True,
    )
    matches = []
    for resource, need in zip(resources, ranked_needs):
        community = community_index[need["community_fips_tract"]]
        equity_score = round((community["vulnerability_index"] * 0.6 + (need["severity"] / 10.0) * 0.4) * 100, 2)
        matches.append(
            Match(
                match_id=str(uuid4()),
                resource_id=resource["resource_id"],
                need_id=need["need_id"],
                equity_score=equity_score,
                routing_plan={
                    "origin": resource["location"]["address"],
                    "destination": need["community_fips_tract"],
                    "distance_km": round(10 + (100 - equity_score) / 8, 1),
                    "eta_hours": round(1.0 + (100 - equity_score) / 40, 1),
                },
                status="recommended",
            ).to_dict()
        )
    delta = 1.0
    if previous_matches:
        previous_scores = sorted(match["equity_score"] for match in previous_matches)
        current_scores = sorted(match["equity_score"] for match in matches)
        if previous_scores and current_scores:
            delta = round(
                sum(abs(current - previous) for current, previous in zip(current_scores, previous_scores)) / len(current_scores),
                4,
            )
    return {"matches": matches, "delta": delta}


MatchOptimizer = Agent(
    name="MatchOptimizer",
    model="gemini-2.5-flash",
    description="Iteratively allocates resources to needs using equity-weighted scoring.",
    instruction="Use the tool to optimize resource-to-need matches. Return JSON only.",
    tools=[optimize_matches],
    output_key="match_optimizer_output",
)
