"""
Unit tests for ResourceScanner agent (CS-02 / B3)

Tests:
- scan() loads resources from bundled fallback data
- FR-003: at least 3 source categories
- A2A message shape (CF-04)
- Filtering by type and location
"""
import copy
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.relieflink_agents.resource_scanner import (
    ResourceScanner,
    build_resources_summary,
    _agency_source_category,
)
from services.relieflink_agents.models import Resource, ResourceType, ResourceStatus, Location


class TestResourceScannerScan:
    def setup_method(self):
        self.scanner = ResourceScanner()

    def test_scan_returns_resources(self):
        result = self.scanner.scan(state="FL")
        assert "resources" in result
        assert len(result["resources"]) > 0

    def test_fr003_at_least_3_source_categories(self):
        """FR-003: Must aggregate from at least 3 source categories."""
        result = self.scanner.scan(state="FL")
        assert result["source_count"] >= 3, (
            "Only {} source categories. FR-003 requires >=3. Got: {}".format(
                result["source_count"], result["sources"]
            )
        )

    def test_scan_sources_include_federal_state_ngo(self):
        result = self.scanner.scan(state="FL")
        sources = set(result["sources"])
        assert "federal" in sources
        assert "state" in sources
        assert "ngo" in sources

    def test_scan_with_footprint_filters(self):
        """Resources should be filtered to the disaster footprint counties + federal."""
        result_all = self.scanner.scan(state="FL")
        result_footprint = self.scanner.scan(state="FL", disaster_footprint=["12057"])
        # Footprint-filtered result should be <= total, but not zero (federal always included)
        assert len(result_footprint["resources"]) > 0
        assert len(result_footprint["resources"]) <= len(result_all["resources"])

    def test_scan_returns_agencies(self):
        result = self.scanner.scan(state="FL")
        assert "agencies" in result
        assert len(result["agencies"]) > 0

    def test_all_resources_have_required_fields(self):
        result = self.scanner.scan(state="FL")
        for r in result["resources"]:
            assert r.resource_id, "resource_id must not be empty"
            assert r.type in ResourceType, "type must be valid ResourceType"
            assert r.quantity >= 0, "quantity must be non-negative"
            assert r.owner_agency_id, "owner_agency_id must not be empty"

    def test_no_duplicate_resource_ids_in_footprint_result(self):
        """Federal resources must not appear twice when they also match the footprint."""
        result = self.scanner.scan(state="FL", disaster_footprint=["12057", "12103"])
        ids = [r.resource_id for r in result["resources"]]
        assert len(ids) == len(set(ids)), "Duplicate resource_ids found in scan result"


class TestResourceScannerA2A:
    """CF-04: A2A message contract."""

    def setup_method(self):
        self.scanner = ResourceScanner()

    def test_build_resources_summary_shape(self):
        resources = [
            Resource(type=ResourceType.SUPPLIES, quantity=500, owner_agency_id="FEMA",
                     location=Location(27.9, -82.4, "Tampa", "12057")),
            Resource(type=ResourceType.SHELTER, quantity=400, owner_agency_id="RED_CROSS",
                     location=Location(27.9, -82.4, "Tampa", "12057")),
            Resource(type=ResourceType.PERSONNEL, quantity=60, owner_agency_id="FL_EMA",
                     location=Location(27.9, -82.4, "Tampa", "12103")),
        ]
        msg = build_resources_summary(resources)
        assert "resources_summary" in msg
        summary = msg["resources_summary"]
        assert "by_type" in summary
        assert "by_location" in summary
        assert "total_available" in summary
        assert summary["by_type"]["supplies"] == 500
        assert summary["by_type"]["shelter"] == 400
        assert summary["total_available"] == 960

    def test_a2a_receive_stores_needs_summary(self):
        needs_msg = {"needs_summary": {"by_type": {"shelter": 800}, "by_severity": {"high": 5}}}
        self.scanner.receive_a2a_message(needs_msg)
        assert self.scanner._received_needs_summary is not None
        assert self.scanner._received_needs_summary["needs_summary"]["by_type"]["shelter"] == 800

    def test_get_a2a_message_from_scan_result(self):
        result = self.scanner.scan(state="FL")
        msg = self.scanner.get_a2a_message(result["resources"])
        assert "resources_summary" in msg
        assert msg["resources_summary"]["total_available"] > 0

    def test_a2a_summary_excludes_allocated_resources(self):
        """build_resources_summary must skip non-AVAILABLE resources."""
        resources = [
            Resource(type=ResourceType.SUPPLIES, quantity=500, owner_agency_id="FEMA",
                     status=ResourceStatus.AVAILABLE),
            Resource(type=ResourceType.SUPPLIES, quantity=200, owner_agency_id="FEMA",
                     status=ResourceStatus.ALLOCATED),
        ]
        msg = build_resources_summary(resources)
        # Only the 500 available units should count
        assert msg["resources_summary"]["by_type"]["supplies"] == 500
        assert msg["resources_summary"]["total_available"] == 500


class TestResourceScannerFiltering:
    def setup_method(self):
        self.scanner = ResourceScanner()
        result = self.scanner.scan(state="FL")
        # Bug fix: deep-copy the list so status mutations in one test do not
        # pollute other test methods that share the same setup_method data.
        self.resources = copy.deepcopy(result["resources"])

    def test_get_resources_by_type_supplies(self):
        supplies = self.scanner.get_resources_by_type(self.resources, ResourceType.SUPPLIES)
        assert all(r.type == ResourceType.SUPPLIES for r in supplies)

    def test_get_resources_by_type_all_available(self):
        """Filter should only return AVAILABLE resources."""
        if not self.resources:
            pytest.skip("No resources loaded")

        # Find any supplies resource and mark it allocated
        supplies = [r for r in self.resources if r.type == ResourceType.SUPPLIES]
        if not supplies:
            pytest.skip("No supplies resources to test with")

        target = supplies[0]
        target.status = ResourceStatus.ALLOCATED

        filtered = self.scanner.get_resources_by_type(self.resources, ResourceType.SUPPLIES)
        # Confirm no ALLOCATED resources are returned
        assert all(r.status == ResourceStatus.AVAILABLE for r in filtered)
        # Confirm the allocated resource_id is not present
        filtered_ids = {r.resource_id for r in filtered}
        assert target.resource_id not in filtered_ids


class TestResourceScannerEdgeCases:
    """Issues 3-5: invalid records, get_resources_near_county."""

    def setup_method(self):
        self.scanner = ResourceScanner()

    def test_invalid_resource_type_skipped(self, tmp_path):
        """Invalid resource type enum value returns None from _parse_resource — record skipped."""
        import json
        from services.relieflink_agents.resource_scanner import _parse_resource
        bad_record = {
            "resource_id": "bad-001",
            "type": "INVALID_TYPE",
            "subtype": "test",
            "quantity": 10,
            "location": {"lat": 27.9, "lon": -82.4, "address": "Test", "fips_code": "12057"},
            "owner_agency_id": "FEMA",
            "status": "available",
        }
        result = _parse_resource(bad_record)
        assert result is None

    def test_invalid_resource_status_defaults_to_available(self):
        """Invalid status enum falls back to AVAILABLE."""
        from services.relieflink_agents.resource_scanner import _parse_resource
        record = {
            "resource_id": "bad-002",
            "type": "supplies",
            "subtype": "test",
            "quantity": 5,
            "location": {"lat": 27.9, "lon": -82.4, "address": "Test", "fips_code": "12057"},
            "owner_agency_id": "FEMA",
            "status": "INVALID_STATUS",
        }
        result = _parse_resource(record)
        assert result is not None
        from services.relieflink_agents.models import ResourceStatus
        assert result.status == ResourceStatus.AVAILABLE

    def test_malformed_agency_skipped(self):
        """Agency record missing required fields returns None."""
        from services.relieflink_agents.resource_scanner import _parse_agency
        bad_agency = {"name": "Test Agency"}  # missing agency_id, type, jurisdiction
        result = _parse_agency(bad_agency)
        assert result is None

    def test_get_resources_near_county(self):
        """get_resources_near_county returns only available resources in given county."""
        result = self.scanner.scan(state="FL", disaster_footprint=["12057"])
        resources = result["resources"]
        nearby = self.scanner.get_resources_near_county(resources, "12057")
        assert all(r.location and r.location.fips_code == "12057" for r in nearby)
        from services.relieflink_agents.models import ResourceStatus
        assert all(r.status == ResourceStatus.AVAILABLE for r in nearby)


class TestAgencySourceCategory:
    def test_fema_is_federal(self):
        assert _agency_source_category("FEMA") == "federal"

    def test_fl_ema_is_state(self):
        assert _agency_source_category("FL_EMA") == "state"

    def test_red_cross_is_ngo(self):
        assert _agency_source_category("RED_CROSS") == "ngo"

    def test_voad_is_volunteer(self):
        assert _agency_source_category("VOAD_PINELLAS") == "volunteer"

    def test_cert_is_volunteer(self):
        assert _agency_source_category("MANATEE_CERT") == "volunteer"

    def test_unknown_agency_defaults_to_ngo(self):
        assert _agency_source_category("UNKNOWN_ORG") == "ngo"
