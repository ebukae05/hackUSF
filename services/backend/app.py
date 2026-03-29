from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.backend.config import get_settings
from services.backend.pipeline import PipelineTimeoutError, ReliefLinkPipeline

PIPELINE_TIMEOUT_SECONDS = 120


def _match_payload(match) -> dict:
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
                        "message": "The ReliefLink agent pipeline exceeded the 120 second timeout.",
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
                "resources": [resource.to_dict() for resource in snapshot.resources],
                "communities": [community.to_dict() for community in snapshot.communities],
                "needs": [need.to_dict() for need in snapshot.needs],
                "agencies": [agency.to_dict() for agency in snapshot.agencies],
                "summary": {
                    "total_resources": len(snapshot.resources),
                    "total_needs": len(snapshot.needs),
                    "matched": len(snapshot.matches),
                    "pending": sum(1 for match in snapshot.matches if match.status == "recommended"),
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
            return jsonify({"error": "MATCH_NOT_FOUND", "message": f"No match found for {match_id}."}), 404
        return jsonify(result)

    return app


app = create_app()
