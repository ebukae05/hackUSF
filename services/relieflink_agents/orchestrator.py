"""
ReliefLink Pipeline Orchestrator — B1 (CS-04).

Wires the full ADK pipeline:
  SequentialAgent:
    Stage 1: DisasterMonitorAgent (writes disaster_event to session state)
    Stage 2: ParallelAgent(ResourceScannerAgent, NeedMapperAgent) (FR-012)
    Stage 3: MatchOptimizerAgent wrapping LoopAgent (FR-013, FR-015)

FRs: FR-012 (ParallelAgent), FR-015 (SequentialAgent)
Reference: docs/SYSTEM_DESIGN.md Section 1.3.B (B1), 1.3.A (agent timeline)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from services.relieflink_agents.disaster_monitor import DisasterMonitorAgent
from services.relieflink_agents.need_mapper_agent import NeedMapperAgent
from services.relieflink_agents.resource_scanner_agent import ResourceScannerAgent
from services.relieflink_agents.match_optimizer import MatchOptimizerAgent

logger = logging.getLogger(__name__)

PIPELINE_TIMEOUT_SECONDS = 120
DEFAULT_STATE = "FL"
# Tampa Bay demo footprint: Hillsborough, Pinellas, Manatee, Pasco
DEFAULT_FOOTPRINT = ["12057", "12103", "12081", "12101"]


def _build_pipeline(state: str = DEFAULT_STATE, footprint: list[str] | None = None) -> SequentialAgent:
    fp = footprint or DEFAULT_FOOTPRINT
    return SequentialAgent(
        name="ReliefLinkOrchestrator",
        description="Sequential pipeline: disaster detection → parallel resource+need mapping → match optimization.",
        sub_agents=[
            DisasterMonitorAgent(state=state),
            ParallelAgent(
                name="ReliefLinkParallelIngestion",
                description="Runs ResourceScanner and NeedMapper concurrently (FR-012).",
                sub_agents=[
                    ResourceScannerAgent(state=state, disaster_footprint=fp),
                    NeedMapperAgent(disaster_footprint=fp, disaster_severity=8.5, disaster_type="hurricane"),
                ],
            ),
            MatchOptimizerAgent(max_iterations=20),
        ],
    )


async def _run_pipeline_async(state: str = DEFAULT_STATE) -> dict[str, Any]:
    from google.adk.agents.invocation_context import InvocationContext

    svc = InMemorySessionService()
    session = await svc.create_session(app_name="relieflink", user_id="operator")
    pipeline = _build_pipeline(state=state)

    ctx = InvocationContext(
        session_service=svc,
        invocation_id=str(uuid.uuid4()),
        agent=pipeline,
        session=session,
    )

    logger.info("ReliefLink pipeline starting. state=%s", state)
    async for _ in pipeline._run_async_impl(ctx):
        pass

    s = ctx.session.state
    match_data = s.get("match_data", {
        "matches": [], "iterations_run": 0, "converged": False, "total_equity_score": 0.0,
    })

    logger.info(
        "Pipeline complete. matches=%d iterations=%d converged=%s",
        len(match_data.get("matches", [])),
        match_data.get("iterations_run", 0),
        match_data.get("converged", False),
    )

    return {
        "disaster_event": s.get("disaster_event", {}),
        "resources": s.get("resource_data", {}).get("resources", []),
        "agencies": s.get("resource_data", {}).get("agencies", []),
        "communities": s.get("needs_data", {}).get("communities", []),
        "needs": s.get("needs_data", {}).get("needs", []),
        "matches": match_data.get("matches", []),
        "status": "complete",
        "metadata": {
            "state": state,
            "iterations_run": match_data.get("iterations_run", 0),
            "converged": match_data.get("converged", False),
            "total_equity_score": match_data.get("total_equity_score", 0.0),
            "orchestrator": "ReliefLinkOrchestrator",
            "parallel_agent": "ReliefLinkParallelIngestion",
            "loop_agent": "ReliefLinkMatchLoop",
            "delta": 0.0 if match_data.get("converged") else 1.0,
        },
    }


# Module-level instance for inspection / ADK Dev UI discovery
ReliefLinkOrchestrator = _build_pipeline()


def run_relieflink_pipeline(
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = PIPELINE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Synchronous entry point. Runs full ADK SequentialAgent → ParallelAgent → LoopAgent pipeline."""
    state = (payload or {}).get("state", DEFAULT_STATE)
    try:
        return asyncio.run(_run_pipeline_async(state=state))
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        return {
            "matches": [], "disaster_event": None,
            "agencies": [], "resources": [], "communities": [], "needs": [],
            "status": "error", "message": str(exc),
        }
