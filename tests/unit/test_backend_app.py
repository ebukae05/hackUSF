from services.backend.app import create_app
from services.backend.pipeline import PipelineTimeoutError, ReliefLinkPipeline


class TimeoutPipeline(ReliefLinkPipeline):
    def run_pipeline(self, timeout_seconds: int = 120) -> dict:
        raise PipelineTimeoutError("timed out")


def test_healthz_reports_service_state():
    app = create_app()
    client = app.test_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload
    assert payload["google_genai_use_vertexai"] == "FALSE"


def test_run_pipeline_returns_completed_job_status():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/run-pipeline")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "completed"
    assert payload["pipeline"]["orchestrator"] == "ReliefLinkOrchestrator"
    assert payload["pipeline"]["ingestion_stage"] == "ReliefLinkParallelIngestion"
    assert payload["pipeline"]["optimization_stage"] == "ReliefLinkMatchLoop"


def test_get_matches_returns_current_matches():
    app = create_app()
    client = app.test_client()
    client.post("/api/run-pipeline")

    response = client.get("/api/matches")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["matches"]) >= 1
    assert len(payload["resources"]) >= 1
    assert len(payload["communities"]) >= 1
    assert len(payload["needs"]) >= 1
    assert len(payload["agencies"]) >= 1
    assert {"equity_score", "resource_id", "need_id", "routing_plan", "status"}.issubset(payload["matches"][0])


def test_match_decision_updates_status_and_reoptimizes():
    app = create_app()
    client = app.test_client()
    client.post("/api/run-pipeline")
    matches = client.get("/api/matches").get_json()["matches"]

    response = client.post(f"/api/matches/{matches[0]['match_id']}/decision", json={"action": "accept"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["new_status"] == "accepted"
    assert payload["reoptimization_triggered"] is True


def test_match_decision_accepts_system_design_contract_key():
    app = create_app()
    client = app.test_client()
    client.post("/api/run-pipeline")
    matches = client.get("/api/matches").get_json()["matches"]

    response = client.post(f"/api/matches/{matches[0]['match_id']}/decision", json={"decision": "skip"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["new_status"] == "skipped"


def test_pipeline_timeout_returns_504():
    app = create_app(pipeline=TimeoutPipeline())
    client = app.test_client()

    response = client.post("/api/run-pipeline")

    assert response.status_code == 504
    payload = response.get_json()
    assert payload["error"] == "PIPELINE_TIMEOUT"
