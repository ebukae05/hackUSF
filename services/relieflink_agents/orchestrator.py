from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent

from services.relieflink_agents.disaster_monitor import DisasterMonitor, build_disaster_event
from services.relieflink_agents.match_optimizer import MatchOptimizer, optimize_matches
from services.relieflink_agents.need_mapper import NeedMapper, build_needs
from services.relieflink_agents.resource_scanner import ResourceScanner, build_resources

MAX_ITERATIONS = 5
CONVERGENCE_THRESHOLD = 0.05
PIPELINE_TIMEOUT_SECONDS = 120

parallel_ingestion = ParallelAgent(
    name="ReliefLinkParallelIngestion",
    description="Runs DisasterMonitor, ResourceScanner, and NeedMapper concurrently.",
    sub_agents=[DisasterMonitor, ResourceScanner, NeedMapper],
)

optimization_loop = LoopAgent(
    name="ReliefLinkMatchLoop",
    description="Runs MatchOptimizer iteratively until convergence or max iterations.",
    sub_agents=[MatchOptimizer],
    max_iterations=MAX_ITERATIONS,
)

ReliefLinkOrchestrator = SequentialAgent(
    name="ReliefLinkOrchestrator",
    description="Runs parallel ingestion followed by iterative match optimization.",
    sub_agents=[parallel_ingestion, optimization_loop],
)


def _execute_pipeline(state: str) -> dict[str, Any]:
    disaster_payload = build_disaster_event(state=state)
    disaster_event = disaster_payload["disaster_event"]
    resource_payload = build_resources(state=state, disaster_footprint=disaster_event["geographic_footprint"])
    need_payload = build_needs(
        state=state,
        disaster_footprint=disaster_event["geographic_footprint"],
        disaster_severity=disaster_event["severity"],
    )

    matches: list[dict[str, Any]] = []
    status = "complete"
    delta = 1.0
    iterations_run = 0

    while iterations_run < MAX_ITERATIONS:
        iterations_run += 1
        optimized = optimize_matches(
            resources=resource_payload["resources"],
            communities=need_payload["communities"],
            needs=need_payload["needs"],
            previous_matches=matches,
        )
        matches = optimized["matches"]
        delta = optimized["delta"]
        if delta < CONVERGENCE_THRESHOLD:
            break

    return {
        "matches": matches,
        "status": status,
        "disaster_event": disaster_event,
        "agencies": resource_payload["agencies"],
        "resources": resource_payload["resources"],
        "communities": need_payload["communities"],
        "needs": need_payload["needs"],
        "metadata": {
            "state": state,
            "iterations_run": iterations_run,
            "delta": delta,
            "orchestrator": ReliefLinkOrchestrator.name,
            "parallel_agent": parallel_ingestion.name,
            "loop_agent": optimization_loop.name,
        },
    }


def run_relieflink_pipeline(payload: dict[str, Any] | None = None, timeout_seconds: int = PIPELINE_TIMEOUT_SECONDS) -> dict[str, Any]:
    payload = payload or {"state": "FL"}
    state = payload.get("state", "FL")
    best_effort: dict[str, Any] = {"matches": [], "status": "error"}

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_pipeline, state)
            try:
                result = future.result(timeout=timeout_seconds)
                best_effort = result
                return result
            except FutureTimeoutError:
                return {
                    "matches": best_effort.get("matches", []),
                    "disaster_event": best_effort.get("disaster_event"),
                    "agencies": best_effort.get("agencies", []),
                    "resources": best_effort.get("resources", []),
                    "communities": best_effort.get("communities", []),
                    "needs": best_effort.get("needs", []),
                    "status": "timeout",
                    "message": f"Pipeline exceeded {timeout_seconds} seconds. Returning best-effort results.",
                }
    except Exception as error:
        return {
            "matches": best_effort.get("matches", []),
            "disaster_event": best_effort.get("disaster_event"),
            "agencies": best_effort.get("agencies", []),
            "resources": best_effort.get("resources", []),
            "communities": best_effort.get("communities", []),
            "needs": best_effort.get("needs", []),
            "status": "error",
            "message": str(error),
        }
