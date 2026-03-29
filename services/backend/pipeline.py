"""
ReliefLink Pipeline state manager.
Stores pipeline results as dicts (JSON-ready) to avoid dataclass reconstruction issues.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from services.relieflink_agents.orchestrator import run_relieflink_pipeline

logger = logging.getLogger(__name__)


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
        self._accepted_ids: set[str] = set()
        self._skipped_ids: set[str] = set()

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

        logger.info("Pipeline starting. job_id=%s", job_id)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_pipeline, job_id, started_at)
            try:
                result = future.result(timeout=timeout_seconds)
                logger.info("Pipeline completed. job_id=%s status=%s", job_id, result.get("status"))
                return result
            except FutureTimeoutError as error:
                logger.warning("Pipeline timeout. job_id=%s timeout_seconds=%d", job_id, timeout_seconds)
                with self._lock:
                    self._snapshot.current_job = {
                        "job_id": job_id,
                        "status": "timeout",
                        "started_at": started_at,
                        "completed_at": utc_now_iso(),
                        "message": f"Pipeline exceeded {timeout_seconds} seconds. Returning partial results.",
                    }
                    # FM-06: return partial results from whatever was written to snapshot
                    return dict(self._snapshot.current_job)
                raise PipelineTimeoutError("Pipeline exceeded 120 seconds.") from error

    def apply_decision(self, match_id: str, action: str) -> dict[str, Any] | None:
        with self._lock:
            target = next((m for m in self._snapshot.matches if m.get("match_id") == match_id), None)
            if target is None:
                return None

            if action == "accept":
                target["status"] = "accepted"
                self._accepted_ids.add(match_id)
            elif action == "modify":
                target["status"] = "modified"
            elif action == "skip":
                target["status"] = "skipped"
                self._skipped_ids.add(match_id)

            reoptimization_triggered = action in {"accept", "skip"}
            if reoptimization_triggered:
                self._reoptimize_locked()

            logger.info(
                "Match decision applied. match_id=%s action=%s new_status=%s reoptimization=%s timestamp=%s",
                match_id, action, target["status"], reoptimization_triggered, utc_now_iso(),
            )
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
        """
        FR-011: Re-run MatchOptimizerAgent on remaining resources/needs after
        operator accept/skip decisions. Accepted matches lock resources/needs;
        skipped matches release them back to the pool.
        Reference: SYSTEM_DESIGN.md CF-07
        """
        from services.relieflink_agents.match_optimizer import (
            MatchOptimizerAgent,
            _dicts_to_resources,
            _dicts_to_needs,
            _dicts_to_communities,
        )
        from services.relieflink_agents.models import Match, MatchStatus

        if not self._snapshot.resources or not self._snapshot.needs:
            return

        resources = _dicts_to_resources(self._snapshot.resources)
        needs = _dicts_to_needs(self._snapshot.needs)
        communities = _dicts_to_communities(self._snapshot.communities)

        previous_matches = [
            Match(
                match_id=m.get("match_id", ""),
                resource_id=m.get("resource_id", ""),
                need_id=m.get("need_id", ""),
                equity_score=m.get("equity_score", 0.0),
                status=MatchStatus(m.get("status", "recommended")),
            )
            for m in self._snapshot.matches
        ]

        try:
            agent = MatchOptimizerAgent(max_iterations=20)
            result = agent.reoptimize(
                resources=resources,
                needs=needs,
                communities=communities,
                accepted_match_ids=list(self._accepted_ids),
                skipped_match_ids=list(self._skipped_ids),
                previous_matches=previous_matches,
            )
            # Preserve accepted/skipped matches, replace pending with fresh results
            preserved = [
                m for m in self._snapshot.matches
                if m.get("status") in {"accepted", "modified", "skipped"}
            ]
            self._snapshot.matches = preserved + result.get("matches", [])
            logger.info(
                "Reoptimization complete. accepted=%d skipped=%d new_matches=%d",
                len(self._accepted_ids), len(self._skipped_ids), len(result.get("matches", [])),
            )
        except Exception as exc:
            logger.error("Reoptimization failed: %s. Keeping existing matches.", exc)
