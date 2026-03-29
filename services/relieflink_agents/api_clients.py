"""
External API client layer (FT-02).
Wrappers for FEMA, NOAA, CDC SVI, Census Geocoder with timeout, pacing, and fallback.
Reference: docs/external_apis/FEMA_API.md, docs/external_apis/NOAA_NWS_API.md,
           docs/external_apis/CDC_SVI.md
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"

_FEMA_BASE = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
_NOAA_BASE = "https://api.weather.gov/alerts/active"
_FEMA_SHELTERS_BASE = (
    "https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/MapServer/0/query"
)
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

_CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"


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


def get_open_shelters(state: str = "FL") -> list[dict]:
    """
    Fetch currently open emergency shelters from FEMA's National Shelter System GIS API.
    Returns list of shelter dicts with name, address, lat/lon, capacity, status.
    Returns [] on failure — non-blocking per system design.
    Reference: https://gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/MapServer/0/query
    Updates every ~20 minutes from FEMA/Red Cross shelter database.
    """
    time.sleep(_PACING)
    params = {
        "where": f"stateabbreviation='{state}' AND status='OPEN'",
        "outFields": (
            "facilityname,address,city,stateabbreviation,zip,"
            "latitude,longitude,evacuationcapacity,postimpactcapacity,"
            "totalpopulation,adacompatible,petsallowed,status"
        ),
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 200,
    }
    for attempt in range(2):
        try:
            resp = requests.get(
                _FEMA_SHELTERS_BASE, params=params, timeout=_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            shelters = [f.get("attributes", {}) for f in features if f.get("attributes")]
            logger.info(
                "get_open_shelters: %d open shelters found for state=%s", len(shelters), state
            )
            return shelters
        except Exception as exc:
            if attempt == 0:
                logger.warning(
                    "FEMA Shelters API attempt 1 failed (%s), retrying in 2s...", exc
                )
                time.sleep(2)
            else:
                logger.warning(
                    "FEMA Shelters API unavailable after 2 attempts (%s). "
                    "Proceeding without live shelter data.", exc
                )
    return []


def load_svi_data(state: str = "FL") -> pd.DataFrame:
    """
    Load CDC SVI data for the given state as a pandas DataFrame.
    Uses bundled fl_svi_subset.csv (live 58MB download not feasible for demo).
    Returns empty DataFrame on failure — callers must handle gracefully (FM-03).
    Reference: docs/external_apis/CDC_SVI.md
    """
    bundled_path = _DATA_DIR / "fl_svi_subset.csv"
    try:
        df = pd.read_csv(bundled_path, dtype={"FIPS": str, "STCNTY": str})
        if state != "FL":
            logger.warning(
                "load_svi_data: bundled SVI data is FL-only; state=%s not fully supported.", state
            )
        logger.info("load_svi_data: loaded %d rows from bundled SVI data.", len(df))
        return df
    except Exception as exc:
        logger.error(
            "load_svi_data: failed to load bundled SVI data: %s. Returning empty DataFrame.", exc
        )
        return pd.DataFrame()


def geocode_address(address: str) -> Optional[str]:
    """
    Convert a street address to a Census tract FIPS code using the Census Geocoder API.
    Returns 11-digit FIPS string or None on failure (non-blocking).
    Reference: docs/external_apis/CDC_SVI.md (address_to_tract example)
    """
    time.sleep(_PACING)
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    for attempt in range(2):
        try:
            resp = requests.get(_CENSUS_GEOCODER_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            matches = resp.json().get("result", {}).get("addressMatches", [])
            if matches:
                tracts = matches[0].get("geographies", {}).get("Census Tracts", [])
                if tracts:
                    return tracts[0]["GEOID"]
            return None
        except Exception as exc:
            if attempt == 0:
                logger.warning("Census Geocoder attempt 1 failed (%s), retrying in 2s...", exc)
                time.sleep(2)
            else:
                logger.warning(
                    "Census Geocoder unavailable after 2 attempts (%s). Returning None.", exc
                )
    return None
