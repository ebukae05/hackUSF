"""
ResourceScanner Agent - CS-02 (B3)

Aggregates resource inventories from 3+ source categories:
  - federal   (FEMA staging areas)
  - state     (FL EMA / FL DOH depots)
  - ngo       (Red Cross, Feeding Tampa Bay, VOAD)
  - volunteer (CERT, Salvation Army, community hubs)

Produces Resource[] with location, quantity, type, owning agency.
Participates in A2A communication with NeedMapper (FR-014 / CF-04).

FRs: FR-003, FR-014
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Agency, AgencyType, Location, Resource, ResourceStatus, ResourceType

logger = logging.getLogger(__name__)

# Path to bundled fallback data (FT-03 / FM-02)
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_FALLBACK_RESOURCES_PATH = _DATA_DIR / "sample_resources.json"


# ---------------------------------------------------------------------------
# A2A message shapes (CF-04)
# ---------------------------------------------------------------------------

def build_resources_summary(resources: List[Resource]) -> Dict[str, Any]:
    """
    Build the A2A message that ResourceScanner sends to NeedMapper.
    Contract: { "resources_summary": { "by_type": {...}, "by_location": {...} } }
    """
    by_type: Dict[str, int] = {}
    by_location: Dict[str, int] = {}

    for r in resources:
        if r.status != ResourceStatus.AVAILABLE:
            continue
        type_key = r.type.value
        by_type[type_key] = by_type.get(type_key, 0) + r.quantity

        loc_key = r.location.fips_code if r.location else "unknown"
        by_location[loc_key] = by_location.get(loc_key, 0) + r.quantity

    return {
        "resources_summary": {
            "by_type": by_type,
            "by_location": by_location,
            "total_available": sum(by_type.values()),
            "source_categories": list(
                {_agency_source_category(r.owner_agency_id) for r in resources}
            ),
        }
    }


def _agency_source_category(agency_id: str) -> str:
    """Map agency_id to source category string."""
    federal = {"FEMA", "ARMY_CORPS", "HHS"}
    state = {"FL_EMA", "FL_DOH", "FL_GUARD"}
    if agency_id in federal:
        return "federal"
    if agency_id in state:
        return "state"
    if "VOAD" in agency_id or "CERT" in agency_id:
        return "volunteer"
    return "ngo"


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_fallback_data() -> Dict[str, Any]:
    """Load bundled sample_resources.json (FT-03)."""
    with open(_FALLBACK_RESOURCES_PATH, "r") as f:
        return json.load(f)


def _parse_resource(raw: Dict[str, Any]) -> Optional[Resource]:
    """
    Parse a raw JSON dict into a Resource dataclass.
    Returns None if required enum fields contain unexpected values so a single
    bad record in the inventory file does not crash the entire scan.
    """
    loc_raw = raw.get("location", {})
    location = (
        Location(
            lat=float(loc_raw.get("lat", 0.0)),
            lon=float(loc_raw.get("lon", 0.0)),
            address=loc_raw.get("address", ""),
            fips_code=loc_raw.get("fips_code", ""),
        )
        if loc_raw
        else None
    )

    try:
        resource_type = ResourceType(raw.get("type", "supplies"))
    except ValueError:
        logger.warning(
            "ResourceScanner: unknown resource type %r in inventory; skipping record.",
            raw.get("type"),
        )
        return None

    try:
        resource_status = ResourceStatus(raw.get("status", "available"))
    except ValueError:
        logger.warning(
            "ResourceScanner: unknown resource status %r; defaulting to 'available'.",
            raw.get("status"),
        )
        resource_status = ResourceStatus.AVAILABLE

    return Resource(
        resource_id=raw.get("resource_id", ""),
        type=resource_type,
        subtype=raw.get("subtype", ""),
        quantity=int(raw.get("quantity", 0)),
        location=location,
        owner_agency_id=raw.get("owner_agency_id", ""),
        status=resource_status,
    )


def _parse_agency(raw: Dict[str, Any]) -> Optional[Agency]:
    """Parse a raw JSON dict into an Agency dataclass. Returns None on bad data."""
    try:
        return Agency(
            agency_id=raw["agency_id"],
            name=raw["name"],
            type=AgencyType(raw["type"]),
            jurisdiction=raw["jurisdiction"],
        )
    except (KeyError, ValueError) as exc:
        logger.warning("ResourceScanner: skipping malformed agency record: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main ResourceScanner logic
# ---------------------------------------------------------------------------

class ResourceScanner:
    """
    B3 - ResourceScanner Agent.

    Aggregates resource inventories from multiple source categories and
    produces a Resource[] list. Also manages A2A coordination with NeedMapper.

    Usage (standalone, no ADK):
        scanner = ResourceScanner()
        result = scanner.scan(state="FL", disaster_footprint=["12057", "12103"])
        resources = result["resources"]

    The scan() method is also called by the ADK agent wrapper in pipeline.py.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or _DATA_DIR
        self._fallback_path = self._data_dir / "sample_resources.json"
        # Holds the most recent A2A message received from NeedMapper
        self._received_needs_summary: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def scan(
        self,
        state: str = "FL",
        disaster_footprint: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate resource inventories for the given state and footprint.

        CF-02 success contract:
          {
            "resources": [Resource, ...],
            "source_count": int,
            "sources": ["federal", "state", "ngo", "volunteer"]
          }

        Falls back to bundled data if no live source available (FM-02 equivalent
        for resource data - there is no live inventory API in the hackathon demo;
        structured demo data IS the authoritative source per CF-02 notes).
        """
        disaster_footprint = disaster_footprint or []

        logger.info(
            "ResourceScanner: scanning resources for state=%s footprint=%s",
            state,
            disaster_footprint,
        )

        resources, agencies = self._load_resources(state, disaster_footprint)

        source_categories = list(
            {_agency_source_category(r.owner_agency_id) for r in resources}
        )

        logger.info(
            "ResourceScanner: found %d resources across %d source categories: %s",
            len(resources),
            len(source_categories),
            source_categories,
        )

        # Validate FR-003: at least 3 source categories
        if len(source_categories) < 3:
            logger.warning(
                "ResourceScanner: only %d source categories found (FR-003 requires >=3). "
                "Available: %s",
                len(source_categories),
                source_categories,
            )

        return {
            "resources": resources,
            "agencies": agencies,
            "source_count": len(source_categories),
            "sources": source_categories,
        }

    def get_a2a_message(self, resources: List[Resource]) -> Dict[str, Any]:
        """
        Build the A2A message to send to NeedMapper (CF-04).
        Called by the pipeline after scan() completes.
        """
        return build_resources_summary(resources)

    def receive_a2a_message(self, needs_summary: Dict[str, Any]) -> None:
        """
        Receive A2A message from NeedMapper (CF-04).
        Stores needs context for potential inventory refinement.
        """
        self._received_needs_summary = needs_summary
        logger.info(
            "ResourceScanner A2A: received needs summary from NeedMapper. by_type=%s",
            needs_summary.get("needs_summary", {}).get("by_type", {}),
        )

    def get_resources_by_type(
        self, resources: List[Resource], resource_type: ResourceType
    ) -> List[Resource]:
        """Filter resources by type, available only."""
        return [
            r for r in resources
            if r.type == resource_type and r.status == ResourceStatus.AVAILABLE
        ]

    def get_resources_near_county(
        self, resources: List[Resource], county_fips: str
    ) -> List[Resource]:
        """Return resources whose location.fips_code matches the county FIPS."""
        return [
            r for r in resources
            if r.location
            and r.location.fips_code == county_fips
            and r.status == ResourceStatus.AVAILABLE
        ]

    # ------------------------------------------------------------------
    # Internal loading
    # ------------------------------------------------------------------

    def _load_resources(
        self,
        state: str,
        disaster_footprint: List[str],
    ) -> Tuple[List[Resource], List[Agency]]:
        """
        Load resource inventories. Uses bundled fallback data.
        For the hackathon demo, structured JSON data IS the inventory source.

        Bug fix: use a set of resource_ids for O(1) deduplication instead of
        'r not in footprint_resources' which was O(n) identity comparison.
        """
        try:
            data = _load_fallback_data()

            raw_resources = data.get("resources", [])
            parsed = [_parse_resource(r) for r in raw_resources]
            all_resources: List[Resource] = [r for r in parsed if r is not None]

            raw_agencies = data.get("agencies", [])
            parsed_agencies = [_parse_agency(a) for a in raw_agencies]
            all_agencies: List[Agency] = [a for a in parsed_agencies if a is not None]

            # Filter to resources in the disaster footprint counties (if specified)
            if disaster_footprint:
                footprint_resources = [
                    r for r in all_resources
                    if r.location and r.location.fips_code in disaster_footprint
                ]
                # Build a set of already-included resource_ids for O(1) dedup
                footprint_ids = {r.resource_id for r in footprint_resources}
                # Also include federal/national resources regardless of location
                federal_resources = [
                    r for r in all_resources
                    if _agency_source_category(r.owner_agency_id) == "federal"
                    and r.resource_id not in footprint_ids
                ]
                resources = footprint_resources + federal_resources
            else:
                resources = all_resources

            # Augment with live FEMA open shelters (federal shelter source)
            live_shelters = self._load_live_shelters(state)
            if live_shelters:
                existing_ids = {r.resource_id for r in resources}
                new_shelter_count = 0
                for shelter in live_shelters:
                    shelter_resource = self._shelter_to_resource(shelter)
                    if shelter_resource and shelter_resource.resource_id not in existing_ids:
                        resources.append(shelter_resource)
                        existing_ids.add(shelter_resource.resource_id)
                        new_shelter_count += 1
                logger.info(
                    "ResourceScanner: added %d live FEMA open shelters", new_shelter_count
                )

            logger.info(
                "ResourceScanner: loaded %d total resources (%s + live shelters)",
                len(resources),
                self._fallback_path,
            )
            return resources, all_agencies

        except Exception as exc:
            logger.error(
                "ResourceScanner: failed to load resource data: %s. "
                "Returning empty resource list.",
                exc,
            )
            return [], []

    def _load_live_shelters(self, state: str) -> List[dict]:
        """Fetch live open shelters from FEMA GIS API. Returns [] on failure (non-blocking)."""
        try:
            from services.relieflink_agents.api_clients import get_open_shelters
            return get_open_shelters(state)
        except Exception as exc:
            logger.warning("ResourceScanner: live shelter fetch failed: %s", exc)
            return []

    def _shelter_to_resource(self, shelter: dict) -> Optional[Resource]:
        """Convert a FEMA shelter dict to a Resource object."""
        import uuid
        try:
            name = shelter.get("facilityname", "Unknown Shelter")
            address = shelter.get("address", "")
            city = shelter.get("city", "")
            zip_code = shelter.get("zip", "")
            lat = float(shelter.get("latitude") or 0.0)
            lon = float(shelter.get("longitude") or 0.0)
            # Use capacity if available, default to 100
            capacity = int(
                shelter.get("evacuationcapacity")
                or shelter.get("postimpactcapacity")
                or 100
            )
            location = Location(
                lat=lat,
                lon=lon,
                address=f"{address}, {city}, FL {zip_code}".strip(", "),
                fips_code="",  # FEMA shelter API doesn't return FIPS directly
            )
            return Resource(
                resource_id=f"shelter-{str(uuid.uuid4())[:8]}",
                type=ResourceType.SHELTER,
                subtype=name,
                quantity=capacity,
                location=location,
                owner_agency_id="FEMA",
                status=ResourceStatus.AVAILABLE,
            )
        except Exception as exc:
            logger.warning("ResourceScanner: failed to parse shelter record: %s", exc)
            return None
