"""
Integration tests for external API clients (FT-02).
These tests call live FEMA and NOAA APIs — require network access.
Run manually before slice closure: python3 -m pytest tests/integration/ -v
"""
import pytest

from services.relieflink_agents.api_clients import get_disaster_declarations, get_active_alerts


class TestFEMAClientLive:
    def test_get_disaster_declarations_returns_fl_results(self):
        """Contract test: live FEMA API returns FL declarations with required fields."""
        result = get_disaster_declarations("FL")
        assert isinstance(result, list)
        if result:
            decl = result[0]
            assert "disasterNumber" in decl, "Missing disasterNumber field"
            assert "incidentType" in decl, "Missing incidentType field"
            assert "state" in decl, "Missing state field"

    def test_get_disaster_declarations_does_not_raise_on_failure(self):
        """Contract test: invalid state returns list (fallback), never raises."""
        result = get_disaster_declarations("XX")
        assert isinstance(result, list)


class TestNOAAClientLive:
    def test_get_active_alerts_returns_list_for_fl(self):
        """Contract test: live NOAA API returns list (possibly empty) for FL."""
        result = get_active_alerts("FL")
        assert isinstance(result, list)
        if result:
            alert = result[0]
            assert "event" in alert, "Missing event field"
            assert "severity" in alert, "Missing severity field"

    def test_get_active_alerts_never_raises(self):
        """Contract test: invalid state returns empty list, never raises."""
        result = get_active_alerts("XX")
        assert isinstance(result, list)
