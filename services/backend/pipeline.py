from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from services.relieflink_agents.models import Agency, Community, DisasterEvent, Match, Need, Resource
from services.relieflink_agents.orchestrator import run_relieflink_pipeline


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineSnapshot:
    disaster_event: DisasterEvent | None = None
    agencies: list[Agency] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    communities: list[Community] = field(default_factory=list)
    needs: list[Need] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)
    current_job: dict[str, Any] | None = None


class PipelineTimeoutError(Exception):
    pass


class ReliefLinkPipeline:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = PipelineSnapshot()

    def get_matches(self) -> list[Match]:
        with self._lock:
            return [Match(**match.to_dict()) for match in self._snapshot.matches]

    def get_snapshot(self) -> PipelineSnapshot:
        with self._lock:
            return PipelineSnapshot(
                disaster_event=None if self._snapshot.disaster_event is None else DisasterEvent(**self._snapshot.disaster_event.to_dict()),
                agencies=[Agency(**agency.to_dict()) for agency in self._snapshot.agencies],
                resources=[Resource(**resource.to_dict()) for resource in self._snapshot.resources],
                communities=[Community(**community.to_dict()) for community in self._snapshot.communities],
                needs=[Need(**need.to_dict()) for need in self._snapshot.needs],
                matches=[Match(**match.to_dict()) for match in self._snapshot.matches],
                current_job=None if self._snapshot.current_job is None else dict(self._snapshot.current_job),
            )

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
            target_match = next((match for match in self._snapshot.matches if match.match_id == match_id), None)
            if target_match is None:
                return None

            if action == "accept":
                target_match.status = "accepted"
            elif action == "modify":
                target_match.status = "modified"
            elif action == "skip":
                target_match.status = "skipped"

            reoptimization_triggered = action in {"accept", "skip"}
            if reoptimization_triggered:
                self._reoptimize_locked()

            return {
                "match_id": match_id,
                "new_status": target_match.status,
                "reoptimization_triggered": reoptimization_triggered,
            }

    def _execute_pipeline(self, job_id: str, started_at: str) -> dict[str, Any]:
        orchestrated = run_relieflink_pipeline({"state": "FL"})
        if orchestrated.get("status") == "error":
            raise RuntimeError(orchestrated.get("message", "Pipeline orchestration failed."))

        disaster_event = DisasterEvent(**orchestrated["disaster_event"])
        agencies = [Agency(**agency) for agency in orchestrated["agencies"]]
        resources = [Resource(**resource) for resource in orchestrated["resources"]]
        communities = [Community(**community) for community in orchestrated["communities"]]
        needs = [Need(**need) for need in orchestrated["needs"]]
        matches = [Match(**match) for match in orchestrated["matches"]]
        iterations_run = orchestrated["metadata"]["iterations_run"]
        converged = orchestrated["metadata"]["delta"] < 0.05
        completed_at = utc_now_iso()

        with self._lock:
            self._snapshot = PipelineSnapshot(
                disaster_event=disaster_event,
                agencies=agencies,
                resources=resources,
                communities=communities,
                needs=needs,
                matches=matches,
                current_job={
                    "job_id": job_id,
                    "status": "completed",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "iterations_run": iterations_run,
                    "converged": converged,
                    "pipeline": {
                        "orchestrator": orchestrated["metadata"]["orchestrator"],
                        "ingestion_stage": orchestrated["metadata"]["parallel_agent"],
                        "optimization_stage": orchestrated["metadata"]["loop_agent"],
                    },
                },
            )
            return dict(self._snapshot.current_job)

    def _reoptimize_locked(self) -> None:
        preserved_statuses = {"accepted", "modified", "skipped"}
        recommended_matches = [match for match in self._snapshot.matches if match.status not in preserved_statuses]
        recommended_matches.sort(key=lambda match: match.equity_score, reverse=True)
        for index, match in enumerate(recommended_matches):
            match.routing_plan["eta_hours"] = round(max(0.5, float(match.routing_plan["eta_hours"]) - 0.1 * index), 1)
