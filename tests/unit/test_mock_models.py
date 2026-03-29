"""Unit tests for core data models (models.py / FT-01)."""
import pytest
from services.relieflink_agents.models import DisasterEvent, DisasterType, NOAAAlert


def make_alert():
    return NOAAAlert(
        alert_id="alert-1",
        event="Hurricane Warning",
        severity="Extreme",
        headline="Hurricane Warning issued for Tampa Bay",
        area_desc="Hillsborough County, FL",
        urgency="Immediate",
        onset="2026-03-29T08:00:00-04:00",
        expires="2026-03-30T08:00:00-04:00",
    )


def make_event(**kwargs):
    defaults = dict(
        disaster_id="4844",
        disaster_type=DisasterType.HURRICANE,
        state="FL",
        declared_date="2026-03-28T00:00:00Z",
        geographic_footprint=["12057", "12103"],
        severity=8.5,
        affected_population=1500000,
        active_alerts=[make_alert()],
    )
    defaults.update(kwargs)
    return DisasterEvent(**defaults)


class TestDisasterEvent:
    def test_all_fields_accessible(self):
        event = make_event()
        assert event.disaster_id == "4844"
        assert event.disaster_type == DisasterType.HURRICANE
        assert event.state == "FL"
        assert event.declared_date == "2026-03-28T00:00:00Z"
        assert event.geographic_footprint == ["12057", "12103"]
        assert event.severity == 8.5
        assert event.affected_population == 1500000
        assert len(event.active_alerts) == 1

    def test_missing_required_field_raises(self):
        with pytest.raises(TypeError):
            DisasterEvent(
                disaster_id="4844",
                disaster_type=DisasterType.HURRICANE,
                # missing state, declared_date, geographic_footprint, severity, affected_population
            )

    def test_empty_geographic_footprint(self):
        event = make_event(geographic_footprint=[])
        assert event.geographic_footprint == []

    def test_severity_min(self):
        event = make_event(severity=0.0)
        assert event.severity == 0.0

    def test_severity_max(self):
        event = make_event(severity=10.0)
        assert event.severity == 10.0

    def test_empty_active_alerts(self):
        event = make_event(active_alerts=[])
        assert event.active_alerts == []

    def test_active_alerts_default_empty(self):
        event = DisasterEvent(
            disaster_id="4844",
            disaster_type=DisasterType.HURRICANE,
            state="FL",
            declared_date="2026-03-28T00:00:00Z",
            geographic_footprint=["12057"],
            severity=5.0,
            affected_population=100000,
        )
        assert event.active_alerts == []


class TestNOAAAlert:
    def test_all_fields_accessible(self):
        alert = make_alert()
        assert alert.alert_id == "alert-1"
        assert alert.event == "Hurricane Warning"
        assert alert.severity == "Extreme"
        assert alert.urgency == "Immediate"

    def test_optional_fields_default_none(self):
        alert = NOAAAlert(
            alert_id="a1", event="Flood Watch", severity="Moderate",
            headline="Flood Watch", area_desc="Miami-Dade", urgency="Expected"
        )
        assert alert.onset is None
        assert alert.expires is None
