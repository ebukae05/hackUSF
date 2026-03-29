from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import relieflink_agents.match_optimizer as match_optimizer_module
from relieflink_agents.match_optimizer import (
    MatchOptimizer,
    _match_identifier,
    calculate_equity_score,
    get_routing_plan,
)
from relieflink_agents.models_temp import Community, Match, MatchStatus, Need, Resource


@pytest.fixture
def routing_stub() -> str:
    return "Route Truck #3 via I-275 N to East Tampa shelter, ETA 14 min"


@pytest.fixture
def optimizer(routing_stub: str, monkeypatch: pytest.MonkeyPatch) -> MatchOptimizer:
    monkeypatch.setattr(
        match_optimizer_module,
        "get_routing_plan",
        lambda match, community: routing_stub,
    )
    return MatchOptimizer(max_iterations=5)


@pytest.fixture
def sample_communities() -> list[Community]:
    return [
        Community(
            id="c-1",
            zip_code="33620",
            name="East Tampa",
            svi_score=9.1,
            lat=28.0587,
            lon=-82.4139,
            population=1000,
        ),
        Community(
            id="c-2",
            zip_code="33701",
            name="St. Petersburg",
            svi_score=6.5,
            lat=27.7676,
            lon=-82.6403,
            population=900,
        ),
        Community(
            id="c-3",
            zip_code="33510",
            name="Brandon",
            svi_score=3.8,
            lat=27.9378,
            lon=-82.2859,
            population=950,
        ),
    ]


@pytest.fixture
def sample_resources() -> list[Resource]:
    return [
        Resource(
            id="r-1",
            type="water",
            quantity=30,
            unit="cases",
            source_agency="FEMA",
            hub_location=(28.0587, -82.4139),
        ),
        Resource(
            id="r-2",
            type="water",
            quantity=30,
            unit="cases",
            source_agency="Red Cross",
            hub_location=(27.9506, -82.4572),
        ),
        Resource(
            id="r-3",
            type="water",
            quantity=30,
            unit="cases",
            source_agency="County Logistics",
            hub_location=(27.9378, -82.2859),
        ),
    ]


@pytest.fixture
def sample_needs() -> list[Need]:
    return [
        Need(
            id="n-1",
            community_id="c-1",
            resource_type="water",
            quantity_needed=30,
            severity=9,
        ),
        Need(
            id="n-2",
            community_id="c-2",
            resource_type="water",
            quantity_needed=30,
            severity=7,
        ),
        Need(
            id="n-3",
            community_id="c-3",
            resource_type="water",
            quantity_needed=30,
            severity=4,
        ),
    ]


@pytest.fixture
def routing_match() -> Match:
    return Match(
        resource_id="r-1",
        need_id="n-1",
        community_id="c-1",
        equity_score=8.9,
        quantity_allocated=30,
        routing_plan="placeholder",
        status=MatchStatus.PENDING,
    )


def test_equity_score_formula(sample_communities: list[Community]) -> None:
    high_need = Need(
        id="n-high",
        community_id="c-1",
        resource_type="water",
        quantity_needed=20,
        severity=9,
    )
    low_need = Need(
        id="n-low",
        community_id="c-3",
        resource_type="water",
        quantity_needed=20,
        severity=4,
    )

    high_score = calculate_equity_score(
        need=high_need,
        community=sample_communities[0],
        hub_location=(28.0587, -82.4139),
    )
    low_score = calculate_equity_score(
        need=low_need,
        community=sample_communities[2],
        hub_location=(27.9378, -82.2859),
    )

    assert high_score > low_score


def test_loop_convergence(
    optimizer: MatchOptimizer,
    sample_resources: list[Resource],
    sample_needs: list[Need],
    sample_communities: list[Community],
    routing_stub: str,
) -> None:
    matches = optimizer.optimize(
        resources=sample_resources,
        needs=sample_needs,
        communities=sample_communities,
    )

    assert len(matches) == 3
    assert all(match.equity_score > 0 for match in matches)
    assert all(match.routing_plan == routing_stub for match in matches)


def test_max_iterations_fallback(
    monkeypatch: pytest.MonkeyPatch,
    sample_resources: list[Resource],
    sample_needs: list[Need],
    sample_communities: list[Community],
) -> None:
    monkeypatch.setattr(
        match_optimizer_module,
        "get_routing_plan",
        lambda match, community: "Dispatch manually",
    )
    optimizer = MatchOptimizer(max_iterations=1)

    matches = optimizer.optimize(
        resources=sample_resources,
        needs=sample_needs,
        communities=sample_communities,
    )

    assert matches
    assert len(matches) == 1


def test_reoptimize_removes_accepted(
    optimizer: MatchOptimizer,
    sample_resources: list[Resource],
    sample_needs: list[Need],
    sample_communities: list[Community],
) -> None:
    initial_matches = optimizer.optimize(
        resources=sample_resources,
        needs=sample_needs,
        communities=sample_communities,
    )

    accepted_match = initial_matches[0]
    fresh_matches = optimizer.reoptimize(
        accepted_match_ids=[_match_identifier(accepted_match)],
        skipped_match_ids=[],
    )

    assert all(match.resource_id != accepted_match.resource_id for match in fresh_matches)
    assert all(match.need_id != accepted_match.need_id for match in fresh_matches)


def test_gemini_retry(
    sample_communities: list[Community],
    routing_match: Match,
) -> None:
    attempts = {"count": 0}

    def generate_content(prompt: str) -> Mock:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary Gemini failure")
        response = Mock()
        response.text = "Route Truck #3 via I-275 N to East Tampa shelter, ETA 14 min"
        return response

    mock_model = Mock()
    mock_model.generate_content.side_effect = generate_content
    mock_genai = Mock()
    mock_genai.GenerativeModel.return_value = mock_model

    with patch.object(match_optimizer_module, "genai", mock_genai):
        plan = get_routing_plan(routing_match, sample_communities[0])

    assert attempts["count"] == 3
    assert plan == "Route Truck #3 via I-275 N to East Tampa shelter, ETA 14 min"
