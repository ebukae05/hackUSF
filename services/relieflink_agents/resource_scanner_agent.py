"""
ResourceScannerAgent — ADK BaseAgent wrapper for B3 (CS-02).

Wraps the ResourceScanner logic as a Google ADK BaseAgent so it can participate
in ParallelAgent orchestration (FR-012) and A2A communication with NeedMapper (FR-014).

A2A (CF-04):
  - Writes `a2a_resources_summary` to session state → NeedMapper reads it
  - Reads  `a2a_needs_summary`     from session state ← NeedMapper writes it
  Transport: Google ADK session state (in-process A2A per system design deviation)

Output key: "resource_data" — read by B1 Orchestration after ParallelAgent completes.

FRs: FR-003, FR-014
Reference: docs/SYSTEM_DESIGN.md Section 1.3.B (B3), 1.3.E (CF-02, CF-04)
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from services.relieflink_agents.resource_scanner import ResourceScanner

logger = logging.getLogger(__name__)

# Session state keys for A2A exchange (CF-04)
A2A_RESOURCES_SUMMARY_KEY = "a2a_resources_summary"
A2A_NEEDS_SUMMARY_KEY = "a2a_needs_summary"


class ResourceScannerAgent(BaseAgent):
    """
    ADK BaseAgent wrapping ResourceScanner (B3).
    Participates in A2A with NeedMapper via session state.
    No LLM inference — fully deterministic.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        state: str = "FL",
        disaster_footprint: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(name="ResourceScannerAgent", **kwargs)
        self._state = state
        self._disaster_footprint = disaster_footprint or []

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scanner = ResourceScanner()
        result = scanner.scan(
            state=self._state,
            disaster_footprint=self._disaster_footprint,
        )

        resources = result["resources"]
        agencies = result["agencies"]

        # Build A2A message → NeedMapper (CF-04)
        a2a_msg = scanner.get_a2a_message(resources)
        ctx.session.state[A2A_RESOURCES_SUMMARY_KEY] = a2a_msg["resources_summary"]
        logger.info(
            "ResourceScannerAgent A2A: wrote resources_summary to session state. "
            "total_available=%s",
            a2a_msg["resources_summary"].get("total_available"),
        )

        # Read A2A message from NeedMapper if already available (eventual consistency)
        needs_summary = ctx.session.state.get(A2A_NEEDS_SUMMARY_KEY)
        if needs_summary:
            scanner.receive_a2a_message({"needs_summary": needs_summary})
            logger.info(
                "ResourceScannerAgent A2A: received needs_summary from session state."
            )

        # Write primary output to session state for B1 Orchestration (CF-02)
        ctx.session.state["resource_data"] = {
            "resources": [_resource_to_dict(r) for r in resources],
            "agencies": [_agency_to_dict(a) for a in agencies],
            "source_count": result["source_count"],
            "sources": result["sources"],
        }

        logger.info(
            "ResourceScannerAgent: completed. resources=%d sources=%s",
            len(resources),
            result["sources"],
        )

        if False:
            yield


def _resource_to_dict(r) -> dict:
    return {
        "resource_id": r.resource_id,
        "type": r.type.value,
        "subtype": r.subtype,
        "quantity": r.quantity,
        "location": {
            "lat": r.location.lat,
            "lon": r.location.lon,
            "address": r.location.address,
            "fips_code": r.location.fips_code,
        } if r.location else None,
        "owner_agency_id": r.owner_agency_id,
        "status": r.status.value,
    }


def _agency_to_dict(a) -> dict:
    return {
        "agency_id": a.agency_id,
        "name": a.name,
        "type": a.type.value,
        "jurisdiction": a.jurisdiction,
    }
