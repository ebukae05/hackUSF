"""
Unit tests for NeedMapper agent (CS-02 / B4)

Tests:
- FR-004: communities identified with vulnerability scores from SVI
- FR-005: needs quantified with severity scores
- FR-006: equity scores computed per MDR-03
- FM-03: fallback to bundled SVI data
- A2A message shape (CF-04)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.relieflink_agents.need_mapper import NeedMapper, build_needs_summary
from services.relieflink_agents.models import Community, Need, NeedType, SVIThemes


# Tampa Bay county FIPS codes present in our bundled data
TAMPA_BAY_FOOTPRINT = ["12057", "12103", "12081"]  # Hillsborough, Pinellas, Manatee


class TestNeedMapperAssess:
    def setup_method(self):
        self.mapper = NeedMapper()

    def test_assess_returns_communities_and_needs(self):
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.5,
            disaster_type="hurricane",
        )
        assert "communities" in result
        assert "needs" in result
        assert len(result["communities"]) > 0
        assert len(result["needs"]) > 0

    def test_fr004_vulnerability_index_in_0_1(self):
        """FR-004: vulnerability_index (RPL_THEMES) must be in [0, 1]."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        for c in result["communities"]:
            assert 0.0 <= c.vulnerability_index <= 1.0, (
                "Tract {} has vulnerability_index={} out of [0,1]".format(
                    c.fips_tract, c.vulnerability_index
                )
            )

    def test_fr004_communities_have_required_fields(self):
        """FR-004: each community must have fips_tract, county_fips, population, vulnerability."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        for c in result["communities"]:
            assert c.fips_tract, "fips_tract must not be empty"
            assert c.county_fips, "county_fips must not be empty"
            assert c.population >= 0
            assert 0.0 <= c.vulnerability_index <= 1.0

    def test_fr005_needs_have_all_required_types(self):
        """FR-005: needs should cover shelter, supplies, medical, evacuation."""
        result = self.mapper.assess(
            disaster_footprint=["12057"],  # just Hillsborough
            disaster_severity=7.0,
            disaster_type="hurricane",
        )
        need_types = {n.need_type.value for n in result["needs"]}
        assert "shelter" in need_types
        assert "supplies" in need_types
        assert "medical" in need_types
        assert "evacuation" in need_types

    def test_fr005_severity_in_range(self):
        """FR-005: need severity must be in [0, 10]."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        for n in result["needs"]:
            assert 0.0 <= n.severity <= 10.0, (
                "Need {} has severity={} out of [0,10]".format(n.need_id, n.severity)
            )

    def test_fr006_equity_score_in_range(self):
        """FR-006: equity_score must be in [0, 1]."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        for n in result["needs"]:
            assert 0.0 <= n.equity_score <= 1.0, (
                "Need {} has equity_score={} out of [0,1]".format(n.need_id, n.equity_score)
            )

    def test_fr006_high_vulnerability_gets_higher_equity_score(self):
        """FR-006: communities with higher SVI should get higher equity scores."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        needs = result["needs"]
        communities = {c.fips_tract: c for c in result["communities"]}

        sorted_communities = sorted(
            communities.values(), key=lambda c: c.vulnerability_index, reverse=True
        )
        if len(sorted_communities) < 2:
            pytest.skip("Need at least 2 communities to compare equity scores")

        most_vuln = sorted_communities[0]
        least_vuln = sorted_communities[-1]

        most_vuln_needs = [n for n in needs if n.community_fips_tract == most_vuln.fips_tract]
        least_vuln_needs = [n for n in needs if n.community_fips_tract == least_vuln.fips_tract]

        if not most_vuln_needs or not least_vuln_needs:
            pytest.skip("No needs found for comparison communities")

        avg_high = sum(n.equity_score for n in most_vuln_needs) / len(most_vuln_needs)
        avg_low = sum(n.equity_score for n in least_vuln_needs) / len(least_vuln_needs)
        assert avg_high > avg_low, (
            "Most vulnerable (SVI={:.3f}) avg_equity={:.4f} should exceed "
            "least vulnerable (SVI={:.3f}) avg_equity={:.4f}".format(
                most_vuln.vulnerability_index, avg_high,
                least_vuln.vulnerability_index, avg_low,
            )
        )

    def test_needs_sorted_by_equity_score_descending(self):
        """Needs should be returned sorted by equity_score highest first."""
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        scores = [n.equity_score for n in result["needs"]]
        assert scores == sorted(scores, reverse=True), (
            "Needs are not sorted by equity_score descending"
        )

    def test_empty_footprint_returns_empty_results(self):
        result = self.mapper.assess(
            disaster_footprint=[],
            disaster_severity=5.0,
        )
        assert result["communities"] == []
        assert result["needs"] == []

    def test_unknown_county_fips_returns_empty_communities(self):
        """Footprint with FIPS not in SVI data should return empty, not crash."""
        result = self.mapper.assess(
            disaster_footprint=["99999"],  # non-existent county
            disaster_severity=5.0,
        )
        assert "communities" in result
        assert "needs" in result
        # Unknown county not in our bundled data -> empty
        assert result["communities"] == []
        assert result["needs"] == []


class TestNeedMapperFallback:
    """FM-03: fallback to bundled SVI when live data unavailable."""

    def test_uses_bundled_fallback_by_default(self):
        """With no SVI path configured, bundled data is used and still produces results."""
        mapper = NeedMapper()
        result = mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        assert len(result["communities"]) > 0
        # Bundled fallback should set the flag and warning
        assert result.get("fallback_used") is True
        assert "staleness_warning" in result

    def test_fallback_when_explicit_path_does_not_exist(self):
        """When a non-existent svi_csv_path is given, fallback to bundled data."""
        mapper = NeedMapper(svi_csv_path="/nonexistent/path/svi.csv")
        result = mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        # Should fall through to bundled data
        assert len(result["communities"]) > 0
        assert result.get("fallback_used") is True

    def test_explicit_svi_path_takes_priority(self, tmp_path):
        """When svi_csv_path is given and valid, it is used and fallback_used is False."""
        import pandas as pd

        svi_data = {
            "FIPS": ["12057999999"],
            "STATE": ["Florida"],
            "ST_ABBR": ["FL"],
            "STCNTY": ["12057"],
            "COUNTY": ["Hillsborough"],
            "LOCATION": ["Test Tract"],
            "E_TOTPOP": [5000],
            "RPL_THEMES": [0.75],
            "RPL_THEME1": [0.70],
            "RPL_THEME2": [0.68],
            "RPL_THEME3": [0.80],
            "RPL_THEME4": [0.72],
        }
        csv_path = tmp_path / "test_svi.csv"
        pd.DataFrame(svi_data).to_csv(csv_path, index=False)

        mapper = NeedMapper(svi_csv_path=str(csv_path))
        result = mapper.assess(
            disaster_footprint=["12057"],
            disaster_severity=7.0,
        )
        assert len(result["communities"]) == 1
        assert result["communities"][0].vulnerability_index == pytest.approx(0.75, abs=0.01)
        assert not result.get("fallback_used", False)

    def test_cached_dataframe_not_mutated_across_calls(self):
        """
        Bug fix regression: calling assess() twice with different footprints
        must not corrupt the cached DataFrame (previously STCNTY was mutated in-place).
        """
        mapper = NeedMapper()
        result_first = mapper.assess(
            disaster_footprint=["12057"],
            disaster_severity=8.0,
        )
        result_second = mapper.assess(
            disaster_footprint=["12103"],
            disaster_severity=8.0,
        )
        # If the cache was mutated, the second call might return wrong results.
        # Both should succeed and return non-overlapping tracts.
        tracts_first = {c.fips_tract for c in result_first["communities"]}
        tracts_second = {c.fips_tract for c in result_second["communities"]}
        # Hillsborough (12057) and Pinellas (12103) tracts should not overlap
        assert tracts_first.isdisjoint(tracts_second), (
            "Different footprints returned overlapping tracts - DataFrame cache was mutated"
        )


class TestNeedMapperA2A:
    """CF-04: A2A message contracts."""

    def setup_method(self):
        self.mapper = NeedMapper()

    def test_build_needs_summary_shape(self):
        needs = [
            Need(need_type=NeedType.SHELTER, severity=8.0, quantity_needed=400,
                 community_fips_tract="12057010100"),
            Need(need_type=NeedType.SUPPLIES, severity=6.0, quantity_needed=1200,
                 community_fips_tract="12057010100"),
            Need(need_type=NeedType.MEDICAL, severity=9.5, quantity_needed=150,
                 community_fips_tract="12103000400"),
        ]
        msg = build_needs_summary(needs)
        assert "needs_summary" in msg
        summary = msg["needs_summary"]
        assert "by_type" in summary
        assert "by_severity" in summary
        assert summary["by_type"]["shelter"] == 400
        assert summary["by_type"]["supplies"] == 1200
        assert "high" in summary["by_severity"]  # severity >= 7.0
        assert summary["community_count"] == 2

    def test_build_needs_summary_empty_list(self):
        """build_needs_summary on empty list must not crash."""
        msg = build_needs_summary([])
        assert msg["needs_summary"]["total_unfulfilled"] == 0
        assert msg["needs_summary"]["community_count"] == 0

    def test_a2a_receive_stores_resources_summary(self):
        msg = {"resources_summary": {"by_type": {"supplies": 500}, "total_available": 500}}
        self.mapper.receive_a2a_message(msg)
        assert self.mapper._received_resources_summary is not None

    def test_get_a2a_message_after_assess(self):
        result = self.mapper.assess(
            disaster_footprint=TAMPA_BAY_FOOTPRINT,
            disaster_severity=8.0,
        )
        msg = self.mapper.get_a2a_message(result["needs"])
        assert "needs_summary" in msg
        assert msg["needs_summary"]["total_unfulfilled"] > 0
