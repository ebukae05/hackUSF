"""
ReliefLink Core Data Models
Defines all domain entities per SYSTEM_DESIGN.md Section 1.3.D

FT-01: Data Models
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DisasterType(str, Enum):
    HURRICANE = "hurricane"
    FLOOD = "flood"
    TORNADO = "tornado"
    WILDFIRE = "wildfire"
    SEVERE_STORM = "severe_storm"
    COASTAL_STORM = "coastal_storm"
    TROPICAL_STORM = "tropical_storm"
    EARTHQUAKE = "earthquake"
    OTHER = "other"


class ResourceType(str, Enum):
    SUPPLIES = "supplies"
    PERSONNEL = "personnel"
    SHELTER = "shelter"
    FUNDS = "funds"
    EQUIPMENT = "equipment"


class ResourceStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class NeedType(str, Enum):
    SHELTER = "shelter"
    SUPPLIES = "supplies"
    MEDICAL = "medical"
    EVACUATION = "evacuation"
    EQUIPMENT = "equipment"


class MatchStatus(str, Enum):
    RECOMMENDED = "recommended"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    SKIPPED = "skipped"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"


class AgencyType(str, Enum):
    FEDERAL = "federal"
    STATE = "state"
    NGO = "ngo"
    VOLUNTEER = "volunteer"


# ---------------------------------------------------------------------------
# Sub-objects
# ---------------------------------------------------------------------------

@dataclass
class Location:
    """Geographic location with FIPS reference."""
    lat: float
    lon: float
    address: str
    fips_code: str  # county or tract FIPS


@dataclass
class SVIThemes:
    """Individual CDC SVI theme scores (0-1 percentile rankings)."""
    socioeconomic: float      # RPL_THEME1
    household: float          # RPL_THEME2
    minority: float           # RPL_THEME3
    housing_transport: float  # RPL_THEME4


@dataclass
class RoutingPlan:
    """Routing details for a matched resource to community delivery."""
    origin: str          # address or staging area name
    destination: str     # community address or tract centroid
    distance_km: float
    eta_hours: float


@dataclass
class NOAAAlert:
    """A single NOAA NWS weather alert."""
    alert_id: str
    event: str       # e.g. "Hurricane Warning"
    severity: str    # "Extreme" | "Severe" | "Moderate" | "Minor"
    headline: str
    area_desc: str
    urgency: str = "Unknown"   # "Immediate" | "Expected" | "Future" | "Unknown"
    onset: Optional[str] = None
    expires: Optional[str] = None


# ---------------------------------------------------------------------------
# Core Entities
# ---------------------------------------------------------------------------

@dataclass
class Agency:
    """
    An organization that owns or controls resources.
    agency_id is a manually assigned string (e.g. "FEMA", "FL_EMA", "RED_CROSS").
    Source-of-truth: static config loaded at startup.
    """
    agency_id: str
    name: str
    type: AgencyType
    jurisdiction: str


@dataclass
class DisasterEvent:
    """
    Represents a declared disaster with geographic footprint and severity.
    disaster_id: FEMA declaration number (externally generated, string).
    Source-of-truth owner: B2 DisasterMonitor.
    """
    disaster_id: str                    # FEMA declaration number
    disaster_type: DisasterType
    state: str                          # 2-letter abbreviation
    declared_date: str                  # ISO 8601 datetime string
    geographic_footprint: List[str]     # list of FIPS county codes
    severity: float                     # 0-10, computed
    affected_population: int
    active_alerts: List[NOAAAlert] = field(default_factory=list)
    # Staleness tracking (FM-01/02)
    data_source: str = "live"           # "live" | "cached" | "bundled"
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Resource:
    """
    A single available resource unit owned by an agency.
    resource_id: uuid4 generated at inventory time.
    Source-of-truth owner: B3 ResourceScanner.
    """
    resource_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ResourceType = ResourceType.SUPPLIES
    subtype: str = ""                   # e.g. "water_pallets", "medical_team"
    quantity: int = 0
    location: Optional[Location] = None
    owner_agency_id: str = ""           # FK to Agency.agency_id
    status: ResourceStatus = ResourceStatus.AVAILABLE


@dataclass
class Community:
    """
    A census tract affected by the disaster, enriched with SVI vulnerability data.
    fips_tract: 11-digit Census tract FIPS (PK).
    Source-of-truth owner: B4 NeedMapper.
    """
    fips_tract: str                     # 11-digit FIPS tract code
    county_fips: str                    # 5-digit FIPS county code
    state: str                          # 2-letter abbreviation
    population: int
    vulnerability_index: float          # RPL_THEMES, 0-1 (1 = most vulnerable)
    svi_themes: Optional[SVIThemes] = None
    county_name: str = ""


@dataclass
class Need:
    """
    A quantified need for a specific community tract.
    need_id: uuid4 generated at assessment time.
    Source-of-truth owner: B4 NeedMapper; B5 updates quantity_fulfilled.
    """
    need_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    community_fips_tract: str = ""      # FK to Community.fips_tract
    need_type: NeedType = NeedType.SUPPLIES
    severity: float = 0.0              # 0-10, computed from impact + population
    quantity_needed: int = 0
    quantity_fulfilled: int = 0
    # Equity score: vulnerability_index * 0.6 + need_severity_normalized * 0.4
    equity_score: float = 0.0          # 0-1, higher = serve first (MDR-03)


@dataclass
class Match:
    """
    A pairing of an available Resource to an identified Need.
    match_id: uuid4 generated at matching time.
    Source-of-truth owner: B5 MatchOptimizer; B7 updates status from operator.
    """
    match_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str = ""               # FK to Resource.resource_id
    need_id: str = ""                   # FK to Need.need_id
    equity_score: float = 0.0          # 0-100, higher = serve first
    routing_plan: Optional[RoutingPlan] = None
    status: MatchStatus = MatchStatus.RECOMMENDED
    operator_notes: Optional[str] = None
    convergence_note: Optional[str] = None  # Set if FM-04 best-effort allocation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_equity_score(
    vulnerability_index: float,
    need_severity: float,
    vulnerability_weight: float = 0.6,
) -> float:
    """
    Compute equity score per MDR-03:
        equity_score = (vulnerability_index * 0.6) + (need_severity_normalized * 0.4)

    vulnerability_index: 0-1 (RPL_THEMES from CDC SVI)
    need_severity: 0-10 (normalized internally to 0-1)
    vulnerability_weight: 0-1, default 0.6 per MDR-03 (configurable)
    Returns value in [0, 1].

    Bug fix: clamp vulnerability_weight to [0, 1] so a bad caller cannot
    produce a negative severity_weight and invert the scoring direction.
    """
    vulnerability_weight = min(max(vulnerability_weight, 0.0), 1.0)
    need_severity_normalized = min(max(need_severity / 10.0, 0.0), 1.0)
    vulnerability_index = min(max(vulnerability_index, 0.0), 1.0)
    severity_weight = 1.0 - vulnerability_weight
    return round(
        vulnerability_index * vulnerability_weight
        + need_severity_normalized * severity_weight,
        4,
    )
