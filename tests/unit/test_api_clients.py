"""Unit tests for external API clients (FT-02) — P-02: FEMA client, P-03: NOAA client."""
import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from services.relieflink_agents.api_clients import get_disaster_declarations, get_active_alerts


SAMPLE_FEMA_RESPONSE = {
    "DisasterDeclarationsSummaries": [
        {
            "disasterNumber": 4844,
            "declarationTitle": "HURRICANE MILTON",
            "incidentType": "Hurricane",
            "state": "FL",
            "declarationDate": "2024-10-11T00:00:00.000Z",
            "designatedArea": "Hillsborough County",
            "placeCode": "12057",
        }
    ]
}

FALLBACK_DATA = [
    {
        "disasterNumber": 4844,
        "declarationTitle": "HURRICANE MILTON",
        "incidentType": "Hurricane",
        "state": "FL",
        "declarationDate": "2024-10-11T00:00:00.000Z",
        "designatedArea": "Hillsborough County",
        "placeCode": "12057",
    }
]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("services.relieflink_agents.api_clients.time.sleep", lambda _: None)


class TestGetDisasterDeclarations:
    def test_happy_path_returns_declarations(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_FEMA_RESPONSE
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = get_disaster_declarations("FL")
        assert len(result) == 1
        assert result[0]["disasterNumber"] == 4844
        assert result[0]["incidentType"] == "Hurricane"

    def test_http_error_returns_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "services.relieflink_agents.api_clients._DATA_DIR", tmp_path
        )
        fallback_file = tmp_path / "sample_fema_declarations.json"
        fallback_file.write_text(json.dumps(FALLBACK_DATA))

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch("requests.get", return_value=mock_resp):
            result = get_disaster_declarations("FL")
        assert len(result) == 1
        assert result[0]["disasterNumber"] == 4844
        assert result[0]["_fallback"] is True  # fallback tag must be present

    def test_timeout_returns_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "services.relieflink_agents.api_clients._DATA_DIR", tmp_path
        )
        fallback_file = tmp_path / "sample_fema_declarations.json"
        fallback_file.write_text(json.dumps(FALLBACK_DATA))

        with patch("requests.get", side_effect=requests.Timeout):
            result = get_disaster_declarations("FL")
        assert len(result) == 1
        assert result[0]["disasterNumber"] == 4844
        assert result[0]["_fallback"] is True  # fallback tag must be present

    def test_retry_succeeds_on_second_attempt(self):
        mock_resp_fail = MagicMock()
        mock_resp_fail.raise_for_status.side_effect = requests.HTTPError("500")

        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = SAMPLE_FEMA_RESPONSE
        mock_resp_ok.raise_for_status.return_value = None

        with patch("requests.get", side_effect=[mock_resp_fail, mock_resp_ok]):
            result = get_disaster_declarations("FL")
        assert len(result) == 1

    def test_empty_response_returns_empty_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"DisasterDeclarationsSummaries": []}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = get_disaster_declarations("FL")
        assert result == []

    def test_fallback_warning_logged(self, tmp_path, monkeypatch, caplog):
        import logging
        monkeypatch.setattr(
            "services.relieflink_agents.api_clients._DATA_DIR", tmp_path
        )
        (tmp_path / "sample_fema_declarations.json").write_text(json.dumps(FALLBACK_DATA))

        with patch("requests.get", side_effect=requests.Timeout):
            with caplog.at_level(logging.WARNING, logger="services.relieflink_agents.api_clients"):
                get_disaster_declarations("FL")
        assert any("FEMA API" in r.message for r in caplog.records)

    def test_fallback_records_tagged_with_fallback_flag(self, tmp_path, monkeypatch):
        """Issue 1 fix: file-based fallback records must carry _fallback=True."""
        monkeypatch.setattr(
            "services.relieflink_agents.api_clients._DATA_DIR", tmp_path
        )
        (tmp_path / "sample_fema_declarations.json").write_text(json.dumps(FALLBACK_DATA))

        with patch("requests.get", side_effect=requests.Timeout):
            result = get_disaster_declarations("FL")
        assert result, "Expected non-empty fallback data"
        assert all(r.get("_fallback") is True for r in result)

    def test_fallback_file_missing_returns_empty_list(self, tmp_path, monkeypatch, caplog):
        """Issue 3 fix: if fallback file is also missing, return [] and log error."""
        import logging
        monkeypatch.setattr(
            "services.relieflink_agents.api_clients._DATA_DIR", tmp_path
        )
        # No fallback file created — tmp_path is empty
        with patch("requests.get", side_effect=requests.Timeout):
            with caplog.at_level(logging.ERROR, logger="services.relieflink_agents.api_clients"):
                result = get_disaster_declarations("FL")
        assert result == []
        assert any("Failed to load FEMA fallback" in r.message for r in caplog.records)


SAMPLE_NOAA_RESPONSE = {
    "features": [
        {
            "properties": {
                "id": "alert-1",
                "event": "Hurricane Warning",
                "severity": "Extreme",
                "headline": "Hurricane Warning issued for Tampa Bay",
                "areaDesc": "Hillsborough County, FL",
                "urgency": "Immediate",
                "onset": "2026-03-29T08:00:00-04:00",
                "expires": "2026-03-30T08:00:00-04:00",
            }
        }
    ]
}


class TestGetActiveAlerts:
    def test_happy_path_returns_alert_properties(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_NOAA_RESPONSE
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = get_active_alerts("FL")
        assert len(result) == 1
        assert result[0]["event"] == "Hurricane Warning"
        assert result[0]["severity"] == "Extreme"

    def test_http_error_returns_empty_list(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch("requests.get", return_value=mock_resp):
            result = get_active_alerts("FL")
        assert result == []

    def test_timeout_returns_empty_list(self):
        with patch("requests.get", side_effect=requests.Timeout):
            result = get_active_alerts("FL")
        assert result == []

    def test_empty_features_returns_empty_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": []}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = get_active_alerts("FL")
        assert result == []

    def test_feature_missing_properties_skipped(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"features": [{"geometry": {}}, {"properties": {"event": "Flood Watch"}}]}
        mock_resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=mock_resp):
            result = get_active_alerts("FL")
        assert len(result) == 1
        assert result[0]["event"] == "Flood Watch"

    def test_failure_warning_logged(self, caplog):
        import logging
        with patch("requests.get", side_effect=requests.Timeout):
            with caplog.at_level(logging.WARNING, logger="services.relieflink_agents.api_clients"):
                get_active_alerts("FL")
        assert any("NOAA API" in r.message for r in caplog.records)

    def test_retry_succeeds_on_second_attempt(self):
        mock_resp_fail = MagicMock()
        mock_resp_fail.raise_for_status.side_effect = requests.HTTPError("500")
        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = SAMPLE_NOAA_RESPONSE
        mock_resp_ok.raise_for_status.return_value = None
        with patch("requests.get", side_effect=[mock_resp_fail, mock_resp_ok]):
            result = get_active_alerts("FL")
        assert len(result) == 1
