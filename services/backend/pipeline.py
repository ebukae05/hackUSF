"""
ReliefLink Pipeline state manager.
Stores pipeline results as dicts (JSON-ready) to avoid dataclass reconstruction issues.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from services.relieflink_agents.orchestrator import run_relieflink_pipeline


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineSnapshot:
    disaster_event: dict | None = None
    agencies: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)
    communities: list[dict] = field(default_factory=list)
    needs: list[dict] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    current_job: dict[str, Any] | None = None


class PipelineTimeoutError(Exception):
    pass


class ReliefLinkPipeline:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = PipelineSnapshot()

    def get_snapshot(self) -> PipelineSnapshot:
        with self._lock:
            return deepcopy(self._snapshot)

    def run_pipeline(self, timeout_seconds: int = 120) -> dict[str, Any]:
        from uuid import uuid4

        job_id = str(uuid4())
        started_at = utc_now_iso()
        with self._lock:
            self._snapshot.current_job = {
                "job_id": job_id,
                "status": "running",
                "started_at": started_at,
                "pipeline": {
                    "orchestrator": "SequentialAgent",
                    "ingestion_stage": "ParallelAgent",
                    "optimization_stage": "LoopAgent",
                },
            }

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_pipeline, job_id, started_at)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeoutError as error:
                with self._lock:
                    self._snapshot.current_job = {
                        "job_id": job_id,
                        "status": "timeout",
                        "started_at": started_at,
                        "completed_at": utc_now_iso(),
                    }
                raise PipelineTimeoutError("Pipeline exceeded 120 seconds.") from error

    def apply_decision(self, match_id: str, action: str) -> dict[str, Any] | None:
        with self._lock:
            target = next((m for m in self._snapshot.matches if m.get("match_id") == match_id), None)
            if target is None:
                return None

            if action == "accept":
                target["status"] = "accepted"
            elif action == "modify":
                target["status"] = "modified"
            elif action == "skip":
                target["status"] = "skipped"

            reoptimization_triggered = action in {"accept", "skip"}
            if reoptimization_triggered:
                self._reoptimize_locked()

            return {
                "match_id": match_id,
                "new_status": target["status"],
                "reoptimization_triggered": reoptimization_triggered,
            }

    def _execute_pipeline(self, job_id: str, started_at: str) -> dict[str, Any]:
        orchestrated = run_relieflink_pipeline({"state": "FL"})
        if orchestrated.get("status") == "error":
            raise RuntimeError(orchestrated.get("message", "Pipeline orchestration failed."))

        iterations_run = orchestrated.get("metadata", {}).get("iterations_run", 0)
        converged = orchestrated.get("metadata", {}).get("converged", False)
        completed_at = utc_now_iso()

        with self._lock:
            self._snapshot = PipelineSnapshot(
                disaster_event=orchestrated.get("disaster_event"),
                agencies=orchestrated.get("agencies", []),
                resources=orchestrated.get("resources", []),
                communities=orchestrated.get("communities", []),
                needs=orchestrated.get("needs", []),
                matches=orchestrated.get("matches", []),
                current_job={
                    "job_id": job_id,
                    "status": "completed",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "iterations_run": iterations_run,
                    "converged": converged,
                    "pipeline": {
                        "orchestrator": orchestrated.get("metadata", {}).get("orchestrator", "ReliefLinkOrchestrator"),
                        "ingestion_stage": orchestrated.get("metadata", {}).get("parallel_agent", "ReliefLinkParallelIngestion"),
                        "optimization_stage": orchestrated.get("metadata", {}).get("loop_agent", "MatchOptimizationLoop"),
                    },
                },
            )
            return dict(self._snapshot.current_job)

    def _reoptimize_locked(self) -> None:
        preserved = {"accepted", "modified", "skipped"}
        pending = [m for m in self._snapshot.matches if m.get("status") not in preserved]
        pending.sort(key=lambda m: m.get("equity_score", 0), reverse=True)
        for i, match in enumerate(pending):
            if isinstance(match.get("routing_plan"), dict) and "eta_hours" in match["routing_plan"]:
                match["routing_plan"]["eta_hours"] = round(
                    max(0.5, float(match["routing_plan"]["eta_hours"]) - 0.1 * i), 1
                )
