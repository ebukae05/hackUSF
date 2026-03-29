from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.backend.config import get_settings
from services.backend.pipeline import PipelineTimeoutError, ReliefLinkPipeline

logger = logging.getLogger(__name__)

PIPELINE_TIMEOUT_SECONDS = 120


def _match_payload(match) -> dict:
    """Accept both dict and dataclass Match objects."""
    if isinstance(match, dict):
        return {
            "match_id": match.get("match_id"),
            "equity_score": match.get("equity_score"),
            "resource_id": match.get("resource_id"),
            "need_id": match.get("need_id"),
            "routing_plan": match.get("routing_plan"),
            "status": match.get("status"),
        }
    return {
        "match_id": match.match_id,
        "equity_score": match.equity_score,
        "resource_id": match.resource_id,
        "need_id": match.need_id,
        "routing_plan": match.routing_plan,
        "status": match.status,
    }


def create_app(pipeline: ReliefLinkPipeline | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config["PIPELINE"] = pipeline or ReliefLinkPipeline()

    @app.get("/")
    def index():
        settings = get_settings()
        return jsonify(
            {
                "service": settings.service_name,
                "status": "ok",
                "message": "ReliefLink deployment baseline is running.",
            }
        )

    @app.get("/healthz")
    def healthcheck():
        settings = get_settings()
        return jsonify(
            {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "app_env": settings.app_env,
                "google_api_key_configured": settings.google_api_key_present,
                "google_genai_use_vertexai": settings.google_genai_use_vertexai,
            }
        )

    @app.post("/api/run-pipeline")
    def run_pipeline():
        pipeline_runner: ReliefLinkPipeline = app.config["PIPELINE"]
        try:
            job = pipeline_runner.run_pipeline(timeout_seconds=PIPELINE_TIMEOUT_SECONDS)
        except PipelineTimeoutError:
            return (
                jsonify(
                    {
                        "error": "PIPELINE_TIMEOUT",
                        "message": "The ReliefLink agent pipeline exceeded the 120 second timeout. Retry the request or check agent logs for slow API calls.",
                        "timeout_seconds": PIPELINE_TIMEOUT_SECONDS,
                    }
                ),
                504,
            )
        return jsonify(job)

    @app.get("/api/matches")
    def get_matches():
        pipeline_runner: ReliefLinkPipeline = app.config["PIPELINE"]
        snapshot = pipeline_runner.get_snapshot()
        return jsonify(
            {
                "matches": [_match_payload(match) for match in snapshot.matches],
                "disaster_event": snapshot.disaster_event,
                "resources": [r if isinstance(r, dict) else r.to_dict() for r in snapshot.resources],
                "communities": [c if isinstance(c, dict) else c.to_dict() for c in snapshot.communities],
                "needs": [n if isinstance(n, dict) else n.to_dict() for n in snapshot.needs],
                "agencies": [a if isinstance(a, dict) else a.to_dict() for a in snapshot.agencies],
                "summary": {
                    "total_resources": len(snapshot.resources),
                    "total_needs": len(snapshot.needs),
                    "matched": len(snapshot.matches),
                    "pending": sum(1 for match in snapshot.matches if (match.get("status") if isinstance(match, dict) else match.status) == "recommended"),
                },
            }
        )

    @app.post("/api/matches/<match_id>/decision")
    def apply_decision(match_id: str):
        payload = request.get_json(silent=True) or {}
        decision = payload.get("decision", payload.get("action"))
        if decision not in {"accept", "modify", "skip"}:
            return (
                jsonify(
                    {
                        "error": "INVALID_DECISION",
                        "message": 'Expected JSON body {"decision": "accept"|"modify"|"skip"}.',
                    }
                ),
                400,
            )

        pipeline_runner: ReliefLinkPipeline = app.config["PIPELINE"]
        result = pipeline_runner.apply_decision(match_id, decision)
        if result is None:
            logger.warning("MATCH_NOT_FOUND: match_id=%s", match_id)
            return jsonify({"error": "MATCH_NOT_FOUND", "message": f"No match found for match_id={match_id}. Run the pipeline first via POST /api/run-pipeline, then retrieve valid match IDs via GET /api/matches."}), 404
        logger.info(
            "Operator decision: match_id=%s decision=%s new_status=%s reoptimization=%s",
            match_id, decision, result.get("new_status"), result.get("reoptimization_triggered"),
        )
        return jsonify(result)

    return app


app = create_app()
