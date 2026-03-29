"""
Temporary mock data models for CS-01 development.
Replace imports from this module with services.relieflink_agents.models when FT-01 (Ebuka) merges.
Field definitions must exactly match docs/SYSTEM_DESIGN.md Section 1.3.D.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DisasterType(str, Enum):
    HURRICANE = "hurricane"
    FLOOD = "flood"
    TORNADO = "tornado"
    WILDFIRE = "wildfire"
    SEVERE_STORM = "severe_storm"
    COASTAL_STORM = "coastal_storm"
    TROPICAL_STORM = "tropical_storm"
    OTHER = "other"


@dataclass
class NOAAAlert:
    id: str
    event: str
    severity: str  # Extreme, Severe, Moderate, Minor, Unknown
    headline: str
    area_desc: str
    urgency: str
    onset: Optional[str] = None
    expires: Optional[str] = None


@dataclass
class DisasterEvent:
    disaster_id: str                          # FEMA declaration number — PK
    disaster_type: DisasterType               # From FEMA incidentType
    state: str                                # 2-letter abbreviation
    declared_date: str                        # ISO 8601 datetime
    geographic_footprint: List[str]           # List of FIPS county codes
    severity: float                           # 0-10, computed from declaration + NOAA
    affected_population: int                  # Estimated from census data
    active_alerts: List[NOAAAlert] = field(default_factory=list)
