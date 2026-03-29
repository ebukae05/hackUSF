"""
External API client layer (FT-02).
Wrappers for FEMA, NOAA, CDC SVI, Census Geocoder with timeout, pacing, and fallback.
Reference: docs/external_apis/FEMA_API.md, docs/external_apis/NOAA_NWS_API.md
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"

_FEMA_BASE = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
_NOAA_BASE = "https://api.weather.gov/alerts/active"
_TIMEOUT = 10
_PACING = 1.0  # seconds between requests per host


def get_disaster_declarations(state: str) -> list[dict]:
    """
    Fetch active disaster declarations from FEMA OpenFEMA API for the given state.
    Returns list of declaration dicts. Falls back to bundled sample data on failure.
    Reference: docs/external_apis/FEMA_API.md
    """
    time.sleep(_PACING)
    params = {
        "$filter": f"state eq '{state}'",
        "$orderby": "declarationDate desc",
        "$top": 10,
        "$select": (
            "disasterNumber,declarationTitle,declarationType,declarationDate,"
            "incidentType,state,designatedArea,placeCode,"
            "ihProgramDeclared,iaProgramDeclared,paProgramDeclared,hmProgramDeclared,"
            "incidentBeginDate,incidentEndDate"
        ),
    }
    for attempt in range(2):
        try:
            resp = requests.get(_FEMA_BASE, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("DisasterDeclarationsSummaries", [])
        except Exception as exc:
            if attempt == 0:
                logger.warning("FEMA API attempt 1 failed (%s), retrying in 2s...", exc)
                time.sleep(2)
            else:
                logger.warning(
                    "FEMA API unavailable after 2 attempts (%s). Falling back to cached data.", exc
                )
    return _load_fema_fallback()


def _load_fema_fallback() -> list[dict]:
    fallback_path = _DATA_DIR / "sample_fema_declarations.json"
    try:
        with open(fallback_path) as f:
            records = json.load(f)
        # Tag each record so callers can detect file-based fallback vs live data
        for record in records:
            record["_fallback"] = True
        return records
    except Exception as exc:
        logger.error("Failed to load FEMA fallback data: %s", exc)
        return []


_NOAA_HEADERS = {
    "User-Agent": "ReliefLink/1.0",
    "Accept": "application/geo+json",
}


def get_active_alerts(state: str) -> list[dict]:
    """
    Fetch active weather alerts from NOAA NWS API for the given state.
    Returns list of alert property dicts. Returns [] on failure per FM-02
    (proceed without alerts rather than blocking the pipeline).
    Reference: docs/external_apis/NOAA_NWS_API.md
    """
    time.sleep(_PACING)
    for attempt in range(2):
        try:
            resp = requests.get(
                _NOAA_BASE,
                params={"area": state},
                headers=_NOAA_HEADERS,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            features = resp.json().get("features", [])
            return [f["properties"] for f in features if "properties" in f]
        except Exception as exc:
            if attempt == 0:
                logger.warning("NOAA API attempt 1 failed (%s), retrying in 2s...", exc)
                time.sleep(2)
            else:
                logger.warning(
                    "NOAA API unavailable after 2 attempts (%s). Proceeding without active alerts.", exc
                )
    return []
