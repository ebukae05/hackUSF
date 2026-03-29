from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DisasterEvent:
    disaster_id: str
    disaster_type: str
    state: str
    declared_date: str
    geographic_footprint: list[str]
    severity: float
    affected_population: int
    active_alerts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Agency:
    agency_id: str
    name: str
    type: str
    jurisdiction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Resource:
    resource_id: str
    type: str
    subtype: str
    quantity: int
    location: dict[str, Any]
    owner_agency_id: str
    status: str = "available"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Community:
    fips_tract: str
    county_fips: str
    state: str
    population: int
    vulnerability_index: float
    svi_themes: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Need:
    need_id: str
    community_fips_tract: str
    need_type: str
    severity: float
    quantity_needed: int
    quantity_fulfilled: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Match:
    match_id: str
    resource_id: str
    need_id: str
    equity_score: float
    routing_plan: dict[str, Any]
    status: str = "recommended"
    operator_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
