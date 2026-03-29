"""
NeedMapperAgent — ADK BaseAgent wrapper for B4 (CS-02).

Wraps the NeedMapper logic as a Google ADK BaseAgent so it can participate
in ParallelAgent orchestration (FR-012) and A2A communication with ResourceScanner (FR-014).

A2A (CF-04):
  - Writes `a2a_needs_summary`      to session state → ResourceScanner reads it
  - Reads  `a2a_resources_summary`  from session state ← ResourceScanner writes it
  Transport: Google ADK session state (in-process A2A per system design deviation)

Output key: "needs_data" — read by B1 Orchestration after ParallelAgent completes.

FRs: FR-004, FR-005, FR-006, FR-014
Reference: docs/SYSTEM_DESIGN.md Section 1.3.B (B4), 1.3.E (CF-03, CF-04)
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from services.relieflink_agents.need_mapper import NeedMapper
from services.relieflink_agents.resource_scanner_agent import (
    A2A_NEEDS_SUMMARY_KEY,
    A2A_RESOURCES_SUMMARY_KEY,
)

logger = logging.getLogger(__name__)


class NeedMapperAgent(BaseAgent):
    """
    ADK BaseAgent wrapping NeedMapper (B4).
    Participates in A2A with ResourceScanner via session state.
    No LLM inference — fully deterministic.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        disaster_footprint: Optional[List[str]] = None,
        disaster_severity: float = 5.0,
        disaster_type: str = "hurricane",
        **kwargs,
    ):
        super().__init__(name="NeedMapperAgent", **kwargs)
        self._disaster_footprint = disaster_footprint or []
        self._disaster_severity = disaster_severity
        self._disaster_type = disaster_type

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        mapper = NeedMapper()

        # Read A2A message from ResourceScanner if already available (eventual consistency)
        resources_summary = ctx.session.state.get(A2A_RESOURCES_SUMMARY_KEY)
        if resources_summary:
            mapper.receive_a2a_message({"resources_summary": resources_summary})
            logger.info(
                "NeedMapperAgent A2A: received resources_summary from session state."
            )

        result = mapper.assess(
            disaster_footprint=self._disaster_footprint,
            disaster_severity=self._disaster_severity,
            disaster_type=self._disaster_type,
        )

        communities = result["communities"]
        needs = result["needs"]

        # Build A2A message → ResourceScanner (CF-04)
        a2a_msg = mapper.get_a2a_message(needs)
        ctx.session.state[A2A_NEEDS_SUMMARY_KEY] = a2a_msg["needs_summary"]
        logger.info(
            "NeedMapperAgent A2A: wrote needs_summary to session state. "
            "total_unfulfilled=%s",
            a2a_msg["needs_summary"].get("total_unfulfilled"),
        )

        # Write primary output to session state for B1 Orchestration (CF-03)
        output = {
            "communities": [_community_to_dict(c) for c in communities],
            "needs": [_need_to_dict(n) for n in needs],
        }
        if result.get("fallback_used"):
            output["fallback_used"] = True
            output["staleness_warning"] = result.get("staleness_warning", "")

        ctx.session.state["needs_data"] = output

        logger.info(
            "NeedMapperAgent: completed. communities=%d needs=%d fallback=%s",
            len(communities),
            len(needs),
            result.get("fallback_used", False),
        )

        if False:
            yield


def _community_to_dict(c) -> dict:
    return {
        "fips_tract": c.fips_tract,
        "county_fips": c.county_fips,
        "state": c.state,
        "population": c.population,
        "vulnerability_index": c.vulnerability_index,
        "county_name": c.county_name,
        "svi_themes": {
            "socioeconomic": c.svi_themes.socioeconomic,
            "household": c.svi_themes.household,
            "minority": c.svi_themes.minority,
            "housing_transport": c.svi_themes.housing_transport,
        } if c.svi_themes else None,
    }


def _need_to_dict(n) -> dict:
    return {
        "need_id": n.need_id,
        "community_fips_tract": n.community_fips_tract,
        "need_type": n.need_type.value,
        "severity": n.severity,
        "quantity_needed": n.quantity_needed,
        "quantity_fulfilled": n.quantity_fulfilled,
        "equity_score": n.equity_score,
    }
