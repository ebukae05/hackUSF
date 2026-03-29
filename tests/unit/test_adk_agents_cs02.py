"""
Unit tests for ResourceScannerAgent and NeedMapperAgent (FR-014 ADK A2A).
Verifies ADK BaseAgent compliance and in-process A2A via session state.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from google.adk.agents.base_agent import BaseAgent
from services.relieflink_agents.resource_scanner_agent import (
    ResourceScannerAgent,
    A2A_RESOURCES_SUMMARY_KEY,
    A2A_NEEDS_SUMMARY_KEY,
)
from services.relieflink_agents.need_mapper_agent import NeedMapperAgent


TAMPA_BAY = ["12057", "12103", "12081"]


def make_ctx(state_dict=None):
    ctx = MagicMock()
    ctx.session.state = state_dict if state_dict is not None else {}
    return ctx


def run_agent(agent, ctx):
    async def _run():
        async for _ in agent._run_async_impl(ctx):
            pass
    asyncio.run(_run())


class TestResourceScannerAgent:
    def test_is_base_agent_subclass(self):
        agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        assert isinstance(agent, BaseAgent)

    def test_writes_resource_data_to_session_state(self):
        agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        ctx = make_ctx()
        run_agent(agent, ctx)
        assert "resource_data" in ctx.session.state
        rd = ctx.session.state["resource_data"]
        assert "resources" in rd
        assert "source_count" in rd
        assert "sources" in rd
        assert rd["source_count"] >= 3  # FR-003

    def test_writes_a2a_resources_summary_to_session_state(self):
        """FR-014: ResourceScannerAgent must write A2A message to session state."""
        agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        ctx = make_ctx()
        run_agent(agent, ctx)
        assert A2A_RESOURCES_SUMMARY_KEY in ctx.session.state
        summary = ctx.session.state[A2A_RESOURCES_SUMMARY_KEY]
        assert "by_type" in summary
        assert "by_location" in summary
        assert "total_available" in summary

    def test_reads_a2a_needs_summary_if_present(self):
        """FR-014: ResourceScannerAgent reads NeedMapper A2A message if available."""
        agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        ctx = make_ctx({
            A2A_NEEDS_SUMMARY_KEY: {
                "by_type": {"shelter": 400},
                "by_severity": {"high": 5},
                "total_unfulfilled": 400,
                "community_count": 5,
            }
        })
        # Should not raise — A2A receive is advisory
        run_agent(agent, ctx)
        assert "resource_data" in ctx.session.state

    def test_resource_data_contract_has_required_fields(self):
        """CF-02 output contract: resources, source_count, sources."""
        agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        ctx = make_ctx()
        run_agent(agent, ctx)
        rd = ctx.session.state["resource_data"]
        for field in ["resources", "agencies", "source_count", "sources"]:
            assert field in rd, f"Missing CF-02 field: {field}"


class TestNeedMapperAgent:
    def test_is_base_agent_subclass(self):
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        assert isinstance(agent, BaseAgent)

    def test_writes_needs_data_to_session_state(self):
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        ctx = make_ctx()
        run_agent(agent, ctx)
        assert "needs_data" in ctx.session.state
        nd = ctx.session.state["needs_data"]
        assert "communities" in nd
        assert "needs" in nd
        assert len(nd["communities"]) > 0
        assert len(nd["needs"]) > 0

    def test_writes_a2a_needs_summary_to_session_state(self):
        """FR-014: NeedMapperAgent must write A2A message to session state."""
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        ctx = make_ctx()
        run_agent(agent, ctx)
        assert A2A_NEEDS_SUMMARY_KEY in ctx.session.state
        summary = ctx.session.state[A2A_NEEDS_SUMMARY_KEY]
        assert "by_type" in summary
        assert "by_severity" in summary
        assert "total_unfulfilled" in summary

    def test_reads_a2a_resources_summary_if_present(self):
        """FR-014: NeedMapperAgent reads ResourceScanner A2A message if available."""
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        ctx = make_ctx({
            A2A_RESOURCES_SUMMARY_KEY: {
                "by_type": {"supplies": 500},
                "by_location": {"12057": 300},
                "total_available": 500,
                "source_categories": ["federal", "state", "ngo"],
            }
        })
        run_agent(agent, ctx)
        assert "needs_data" in ctx.session.state

    def test_needs_data_contract_has_required_fields(self):
        """CF-03 output contract: communities, needs."""
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        ctx = make_ctx()
        run_agent(agent, ctx)
        nd = ctx.session.state["needs_data"]
        for field in ["communities", "needs"]:
            assert field in nd, f"Missing CF-03 field: {field}"

    def test_equity_scores_present_in_needs(self):
        """FR-006: equity scores must be computed in NeedMapper output."""
        agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        ctx = make_ctx()
        run_agent(agent, ctx)
        needs = ctx.session.state["needs_data"]["needs"]
        assert all("equity_score" in n for n in needs)
        assert all(0.0 <= n["equity_score"] <= 1.0 for n in needs)


class TestA2ABidirectional:
    def test_a2a_exchange_both_directions(self):
        """
        FR-014: Simulate both agents running in sequence (resource first, then need),
        verifying bidirectional A2A via session state.
        """
        shared_state = {}

        # ResourceScanner runs first — writes resources_summary
        rs_agent = ResourceScannerAgent(state="FL", disaster_footprint=TAMPA_BAY)
        rs_ctx = make_ctx(shared_state)
        run_agent(rs_agent, rs_ctx)

        assert A2A_RESOURCES_SUMMARY_KEY in shared_state

        # NeedMapper runs second — reads resources_summary, writes needs_summary
        nm_agent = NeedMapperAgent(
            disaster_footprint=TAMPA_BAY,
            disaster_severity=8.0,
        )
        nm_ctx = make_ctx(shared_state)
        run_agent(nm_agent, nm_ctx)

        assert A2A_NEEDS_SUMMARY_KEY in shared_state
        assert "needs_data" in shared_state
        assert "resource_data" in shared_state

        # Verify A2A message shapes (CF-04 contract)
        res_summary = shared_state[A2A_RESOURCES_SUMMARY_KEY]
        needs_summary = shared_state[A2A_NEEDS_SUMMARY_KEY]
        assert "by_type" in res_summary and "by_location" in res_summary
        assert "by_type" in needs_summary and "by_severity" in needs_summary
