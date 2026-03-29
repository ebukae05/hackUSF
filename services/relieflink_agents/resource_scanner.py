from __future__ import annotations

from typing import Any

from google.adk.agents import Agent

from services.relieflink_agents.models import Agency, Resource


def build_resources(state: str = "FL", disaster_footprint: list[str] | None = None) -> dict[str, Any]:
    agencies = [
        Agency("FEMA", "Federal Emergency Management Agency", "federal", "US"),
        Agency("FL_EMA", "Florida Emergency Management", "state", state),
        Agency("RED_CROSS", "American Red Cross", "ngo", state),
    ]
    resources = [
        Resource(
            resource_id="res-water-1",
            type="supplies",
            subtype="water_pallets",
            quantity=100,
            location={"address": "Tampa Staging Area", "fips_code": "12057", "lat": 27.95, "lon": -82.46},
            owner_agency_id="FEMA",
        ),
        Resource(
            resource_id="res-med-1",
            type="personnel",
            subtype="medical_team",
            quantity=4,
            location={"address": "St. Pete Medical Depot", "fips_code": "12103", "lat": 27.77, "lon": -82.64},
            owner_agency_id="RED_CROSS",
        ),
        Resource(
            resource_id="res-shelter-1",
            type="shelter",
            subtype="temporary_shelter_beds",
            quantity=250,
            location={"address": "Hillsborough Shelter Hub", "fips_code": "12057", "lat": 27.99, "lon": -82.30},
            owner_agency_id="FL_EMA",
        ),
    ]
    return {
        "agencies": [agency.to_dict() for agency in agencies],
        "resources": [resource.to_dict() for resource in resources],
        "source_count": 3,
        "sources": ["federal", "state", "ngo"],
    }


ResourceScanner = Agent(
    name="ResourceScanner",
    model="gemini-2.5-flash",
    description="Builds a structured inventory of disaster response resources.",
    instruction="Use the tool to create a resource inventory for the state. Return JSON only.",
    tools=[build_resources],
    output_key="resource_scanner_output",
)
