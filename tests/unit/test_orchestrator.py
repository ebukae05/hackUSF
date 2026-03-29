from services.relieflink_agents.orchestrator import ReliefLinkOrchestrator, run_relieflink_pipeline


def test_orchestrator_returns_complete_result():
    result = run_relieflink_pipeline({"state": "FL"})

    assert result["status"] == "complete"
    assert len(result["matches"]) == 3
    assert len(result["resources"]) == 3
    assert len(result["communities"]) == 3
    assert len(result["needs"]) == 3
    assert result["metadata"]["orchestrator"] == "ReliefLinkOrchestrator"


def test_orchestrator_is_named_correctly():
    assert ReliefLinkOrchestrator.name == "ReliefLinkOrchestrator"
