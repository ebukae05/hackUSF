"""Unit tests for ReliefLink orchestrator (CS-04 / B1)."""
from unittest.mock import patch

from services.relieflink_agents.orchestrator import ReliefLinkOrchestrator, run_relieflink_pipeline


def test_orchestrator_is_named_correctly():
    assert ReliefLinkOrchestrator.name == "ReliefLinkOrchestrator"


def test_orchestrator_has_correct_sub_agent_names():
    sub_names = [a.name for a in ReliefLinkOrchestrator.sub_agents]
    assert "DisasterMonitorAgent" in sub_names
    assert "ReliefLinkParallelIngestion" in sub_names
    assert "MatchOptimizerAgent" in sub_names


def test_orchestrator_returns_complete_result():
    """FR-015: SequentialAgent orchestration returns complete pipeline result."""
    with patch(
        "services.relieflink_agents.match_optimizer._get_routing_plan",
        return_value=None,
    ):
        result = run_relieflink_pipeline({"state": "FL"})

    assert result["status"] == "complete"
    assert "matches" in result
    assert "resources" in result
    assert "communities" in result
    assert "needs" in result
    assert result["metadata"]["orchestrator"] == "ReliefLinkOrchestrator"
    assert result["metadata"]["parallel_agent"] == "ReliefLinkParallelIngestion"


def test_orchestrator_error_returns_error_status():
    """Pipeline errors are caught and returned as error status, not raised."""
    with patch(
        "services.relieflink_agents.orchestrator._run_pipeline_async",
        side_effect=RuntimeError("simulated failure"),
    ):
        result = run_relieflink_pipeline({"state": "FL"})

    assert result["status"] == "error"
    assert "message" in result
