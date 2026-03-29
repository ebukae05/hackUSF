"""
Unit tests for services/relieflink_agents/models.py (FT-01)

Tests:
- All dataclass fields and defaults
- compute_equity_score formula (MDR-03)
- Enum values
"""
import uuid
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.relieflink_agents.models import (
    Agency,
    AgencyType,
    Community,
    DisasterEvent,
    DisasterType,
    Location,
    Match,
    MatchStatus,
    Need,
    NeedType,
    NOAAAlert,
    Resource,
    ResourceStatus,
    ResourceType,
    RoutingPlan,
    SVIThemes,
    compute_equity_score,
)


class TestComputeEquityScore:
    """MDR-03: equity_score = vulnerability_index * 0.6 + need_severity_normalized * 0.4"""

    def test_max_vulnerability_max_severity(self):
        score = compute_equity_score(1.0, 10.0)
        assert score == pytest.approx(1.0, abs=0.001)

    def test_zero_vulnerability_zero_severity(self):
        score = compute_equity_score(0.0, 0.0)
        assert score == pytest.approx(0.0, abs=0.001)

    def test_default_60_40_weighting(self):
        # vulnerability=0.8, severity=5 → normalized_severity=0.5
        # expected = 0.8*0.6 + 0.5*0.4 = 0.48 + 0.20 = 0.68
        score = compute_equity_score(0.8, 5.0)
        assert score == pytest.approx(0.68, abs=0.001)

    def test_custom_weight(self):
        # 50/50 weighting
        score = compute_equity_score(0.8, 5.0, vulnerability_weight=0.5)
        assert score == pytest.approx(0.65, abs=0.001)

    def test_vulnerability_dominates(self):
        """High vulnerability + low severity > low vulnerability + high severity (60/40 rule)."""
        high_vuln_low_need = compute_equity_score(0.9, 1.0)
        low_vuln_high_need = compute_equity_score(0.1, 9.0)
        assert high_vuln_low_need > low_vuln_high_need

    def test_clamp_out_of_range_inputs(self):
        """Values outside [0,1] and [0,10] are clamped."""
        score_over = compute_equity_score(1.5, 15.0)
        score_normal = compute_equity_score(1.0, 10.0)
        assert score_over == score_normal

        score_under = compute_equity_score(-0.5, -5.0)
        assert score_under == pytest.approx(0.0, abs=0.001)

    def test_result_in_zero_to_one(self):
        import random
        random.seed(42)
        for _ in range(50):
            v = random.uniform(0, 1)
            s = random.uniform(0, 10)
            score = compute_equity_score(v, s)
            assert 0.0 <= score <= 1.0, "Out of range: {} for v={}, s={}".format(score, v, s)

    def test_vulnerability_weight_clamped(self):
        """Bug fix: vulnerability_weight > 1.0 must not produce negative severity_weight."""
        # weight=2.0 used to give severity_weight=-1.0, inverting the formula
        score_bad_weight = compute_equity_score(0.5, 5.0, vulnerability_weight=2.0)
        score_max_weight = compute_equity_score(0.5, 5.0, vulnerability_weight=1.0)
        assert score_bad_weight == score_max_weight, (
            "weight > 1.0 should be clamped to 1.0; got {}".format(score_bad_weight)
        )

        score_neg_weight = compute_equity_score(0.5, 5.0, vulnerability_weight=-1.0)
        score_min_weight = compute_equity_score(0.5, 5.0, vulnerability_weight=0.0)
        assert score_neg_weight == score_min_weight


class TestResourceModel:
    def test_default_resource_id_is_uuid(self):
        r = Resource()
        # Should be a valid UUID string
        uuid.UUID(r.resource_id)

    def test_default_status_available(self):
        r = Resource()
        assert r.status == ResourceStatus.AVAILABLE

    def test_resource_with_location(self):
        loc = Location(lat=27.95, lon=-82.45, address="Tampa, FL", fips_code="12057")
        r = Resource(
            type=ResourceType.SUPPLIES,
            subtype="water_pallets",
            quantity=500,
            location=loc,
            owner_agency_id="FEMA",
        )
        assert r.location.fips_code == "12057"
        assert r.quantity == 500

    def test_resource_type_enum_values(self):
        assert ResourceType.SUPPLIES.value == "supplies"
        assert ResourceType.PERSONNEL.value == "personnel"
        assert ResourceType.SHELTER.value == "shelter"
        assert ResourceType.FUNDS.value == "funds"
        assert ResourceType.EQUIPMENT.value == "equipment"


class TestCommunityModel:
    def test_community_fields(self):
        svi = SVIThemes(socioeconomic=0.75, household=0.68, minority=0.82, housing_transport=0.71)
        c = Community(
            fips_tract="12057010100",
            county_fips="12057",
            state="FL",
            population=4823,
            vulnerability_index=0.8821,
            svi_themes=svi,
            county_name="Hillsborough",
        )
        assert c.vulnerability_index == pytest.approx(0.8821)
        assert c.svi_themes.socioeconomic == pytest.approx(0.75)

    def test_optional_svi_themes(self):
        c = Community(
            fips_tract="12057010100",
            county_fips="12057",
            state="FL",
            population=5000,
            vulnerability_index=0.5,
        )
        assert c.svi_themes is None


class TestNeedModel:
    def test_default_need_id_is_uuid(self):
        n = Need()
        uuid.UUID(n.need_id)

    def test_need_fulfilled_starts_zero(self):
        n = Need(quantity_needed=100)
        assert n.quantity_fulfilled == 0

    def test_need_type_enum(self):
        for nt in NeedType:
            assert isinstance(nt.value, str)


class TestMatchModel:
    def test_default_status_recommended(self):
        m = Match()
        assert m.status == MatchStatus.RECOMMENDED

    def test_default_match_id_is_uuid(self):
        m = Match()
        uuid.UUID(m.match_id)

    def test_match_status_lifecycle(self):
        statuses = [s.value for s in MatchStatus]
        assert "recommended" in statuses
        assert "accepted" in statuses
        assert "modified" in statuses
        assert "skipped" in statuses
        assert "dispatched" in statuses
        assert "delivered" in statuses


class TestDisasterEventModel:
    def test_disaster_event_fields(self):
        alert = NOAAAlert(
            alert_id="a1",
            event="Hurricane Warning",
            severity="Extreme",
            headline="Hurricane Warning in effect",
            area_desc="Hillsborough",
        )
        event = DisasterEvent(
            disaster_id="4830",
            disaster_type=DisasterType.HURRICANE,
            state="FL",
            declared_date="2026-03-25T00:00:00Z",
            geographic_footprint=["12057", "12103"],
            severity=8.5,
            affected_population=1250000,
            active_alerts=[alert],
        )
        assert event.state == "FL"
        assert len(event.geographic_footprint) == 2
        assert len(event.active_alerts) == 1
        assert event.data_source == "live"

    def test_disaster_type_enum(self):
        assert DisasterType.HURRICANE.value == "hurricane"
        assert DisasterType.FLOOD.value == "flood"


class TestAgencyModel:
    def test_agency_types(self):
        a = Agency(agency_id="FEMA", name="FEMA", type=AgencyType.FEDERAL, jurisdiction="National")
        assert a.type == AgencyType.FEDERAL
        assert AgencyType.FEDERAL.value == "federal"
        assert AgencyType.STATE.value == "state"
        assert AgencyType.NGO.value == "ngo"
        assert AgencyType.VOLUNTEER.value == "volunteer"
