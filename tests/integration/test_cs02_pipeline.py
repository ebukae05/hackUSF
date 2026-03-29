"""
Integration tests for CS-02: ResourceScanner + NeedMapper + A2A (CF-04)

Tests the full CS-02 slice:
- Both agents run against bundled data
- A2A bidirectional message exchange works correctly
- Output satisfies all FR-003 through FR-006 and FR-014 contracts
- Output shapes match CF-02 and CF-03 contracts from SYSTEM_DESIGN.md
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.relieflink_agents.resource_scanner import ResourceScanner
from services.relieflink_agents.need_mapper import NeedMapper
from services.relieflink_agents.models import (
    ResourceStatus,
    MatchStatus,
    NeedType,
)

# Tampa Bay disaster scenario (matches bundled FEMA declarations)
DISASTER_FOOTPRINT = ["12057", "12103", "12081"]  # Hillsborough, Pinellas, Manatee
DISASTER_SEVERITY = 8.5
DISASTER_TYPE = "hurricane"


class TestCS02Integration:
    """Full CS-02 slice: ResourceScanner + NeedMapper + A2A."""

    def setup_method(self):
        self.scanner = ResourceScanner()
        self.mapper = NeedMapper()

    def test_full_pipeline_produces_resources_and_needs(self):
        """End-to-end: scan + assess + A2A → resources and needs."""
        # Step 1: ResourceScanner scans
        scan_result = self.scanner.scan(
            state="FL", disaster_footprint=DISASTER_FOOTPRINT
        )
        resources = scan_result["resources"]
        assert len(resources) > 0, "ResourceScanner must produce resources"

        # Step 2: NeedMapper assesses
        assess_result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
            disaster_type=DISASTER_TYPE,
        )
        communities = assess_result["communities"]
        needs = assess_result["needs"]
        assert len(communities) > 0, "NeedMapper must produce communities"
        assert len(needs) > 0, "NeedMapper must produce needs"

        # Step 3: A2A exchange (FR-014 / CF-04)
        resources_msg = self.scanner.get_a2a_message(resources)
        needs_msg = self.mapper.get_a2a_message(needs)

        self.mapper.receive_a2a_message(resources_msg)
        self.scanner.receive_a2a_message(needs_msg)

        # Verify A2A messages were received
        assert self.mapper._received_resources_summary is not None
        assert self.scanner._received_needs_summary is not None

    def test_fr003_source_categories(self):
        """FR-003: resource inventory must cover ≥3 source categories."""
        result = self.scanner.scan(state="FL", disaster_footprint=DISASTER_FOOTPRINT)
        assert result["source_count"] >= 3
        sources = set(result["sources"])
        assert sources >= {"federal", "state", "ngo"}

    def test_fr004_vulnerability_scores_present(self):
        """FR-004: every community must have a valid RPL_THEMES vulnerability index."""
        result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
        )
        for c in result["communities"]:
            assert 0.0 <= c.vulnerability_index <= 1.0
            assert c.fips_tract
            assert c.county_fips

    def test_fr005_need_types_present(self):
        """FR-005: needs must include shelter, supplies, medical, evacuation."""
        result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
            disaster_type=DISASTER_TYPE,
        )
        need_types = {n.need_type for n in result["needs"]}
        required = {NeedType.SHELTER, NeedType.SUPPLIES, NeedType.MEDICAL, NeedType.EVACUATION}
        assert required.issubset(need_types), (
            f"Missing need types: {required - need_types}"
        )

    def test_fr006_equity_scores_reflect_vulnerability_priority(self):
        """FR-006: equity scoring must give vulnerable communities higher priority."""
        result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
        )
        communities_by_vuln = sorted(
            result["communities"], key=lambda c: c.vulnerability_index, reverse=True
        )
        needs_by_community = {}
        for n in result["needs"]:
            needs_by_community.setdefault(n.community_fips_tract, []).append(n.equity_score)

        if len(communities_by_vuln) >= 2:
            top_vuln = communities_by_vuln[0]
            bot_vuln = communities_by_vuln[-1]

            top_scores = needs_by_community.get(top_vuln.fips_tract, [0])
            bot_scores = needs_by_community.get(bot_vuln.fips_tract, [0])

            avg_top = sum(top_scores) / len(top_scores)
            avg_bot = sum(bot_scores) / len(bot_scores)

            assert avg_top >= avg_bot, (
                "Most vulnerable community should have ≥ equity score than least vulnerable. "
                f"Top SVI={top_vuln.vulnerability_index:.3f} avg_equity={avg_top:.4f}, "
                f"Bot SVI={bot_vuln.vulnerability_index:.3f} avg_equity={avg_bot:.4f}"
            )

    def test_fr014_a2a_message_contracts(self):
        """FR-014: A2A messages must match CF-04 contract shapes."""
        scan_result = self.scanner.scan(state="FL", disaster_footprint=DISASTER_FOOTPRINT)
        assess_result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
        )

        # ResourceScanner → NeedMapper message
        resources_msg = self.scanner.get_a2a_message(scan_result["resources"])
        assert "resources_summary" in resources_msg
        assert "by_type" in resources_msg["resources_summary"]
        assert "by_location" in resources_msg["resources_summary"]

        # NeedMapper → ResourceScanner message
        needs_msg = self.mapper.get_a2a_message(assess_result["needs"])
        assert "needs_summary" in needs_msg
        assert "by_type" in needs_msg["needs_summary"]
        assert "by_severity" in needs_msg["needs_summary"]

    def test_cf02_output_contract(self):
        """CF-02: ResourceScanner output must include resources, source_count, sources."""
        result = self.scanner.scan(state="FL", disaster_footprint=DISASTER_FOOTPRINT)
        assert "resources" in result
        assert "source_count" in result
        assert "sources" in result
        assert isinstance(result["source_count"], int)
        assert isinstance(result["sources"], list)

    def test_cf03_output_contract(self):
        """CF-03: NeedMapper output must include communities and needs."""
        result = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=DISASTER_SEVERITY,
        )
        assert "communities" in result
        assert "needs" in result
        assert isinstance(result["communities"], list)
        assert isinstance(result["needs"], list)

    def test_all_available_resources_are_status_available(self):
        result = self.scanner.scan(state="FL", disaster_footprint=DISASTER_FOOTPRINT)
        for r in result["resources"]:
            assert r.status == ResourceStatus.AVAILABLE

    def test_multiple_counties_produces_more_communities(self):
        """More counties in footprint → more communities identified."""
        single_county = self.mapper.assess(
            disaster_footprint=["12057"],
            disaster_severity=8.0,
        )
        three_counties = self.mapper.assess(
            disaster_footprint=DISASTER_FOOTPRINT,
            disaster_severity=8.0,
        )
        assert len(three_counties["communities"]) > len(single_county["communities"])
        assert len(three_counties["needs"]) > len(single_county["needs"])
