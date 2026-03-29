from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

BACKEND_URL = os.getenv("RELIEFLINK_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(page_title="ReliefLink", layout="wide")


def _get_json(path: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = requests.get(f"{BACKEND_URL}{path}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error
            if attempt == 0:
                time.sleep(2)
    raise last_error or RuntimeError("GET request failed.")


def _post_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"{BACKEND_URL}{path}", json=payload or {}, timeout=120)
    response.raise_for_status()
    return response.json()


def _vulnerability_band(score: float) -> tuple[str, list[int]]:
    if score >= 0.75:
        return "High", [205, 58, 58]
    if score >= 0.4:
        return "Medium", [214, 170, 0]
    return "Low", [46, 125, 50]


def _resources_table(resources: list[dict[str, Any]], agencies: dict[str, str]) -> pd.DataFrame:
    rows = []
    for resource in resources:
        rows.append(
            {
                "Type": resource["type"],
                "Quantity": resource["quantity"],
                "Location": resource["location"]["address"],
                "Owning Agency": agencies.get(resource["owner_agency_id"], resource["owner_agency_id"]),
            }
        )
    return pd.DataFrame(rows)


def _community_points(communities: list[dict[str, Any]], needs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    need_by_tract = {need["community_fips_tract"]: need for need in needs}
    county_centers = {
        "12057": {"lat": 27.95, "lon": -82.46, "county": "Hillsborough"},
        "12103": {"lat": 27.84, "lon": -82.79, "county": "Pinellas"},
    }
    tract_offsets = {}
    points = []
    for community in communities:
        base = county_centers.get(community["county_fips"], {"lat": 27.70, "lon": -82.40, "county": "Florida"})
        offset = tract_offsets.get(community["county_fips"], 0)
        tract_offsets[community["county_fips"]] = offset + 1
        vulnerability_label, color = _vulnerability_band(float(community["vulnerability_index"]))
        need = need_by_tract.get(community["fips_tract"], {})
        points.append(
            {
                "lat": round(base["lat"] + offset * 0.08, 4),
                "lon": round(base["lon"] + offset * 0.08, 4),
                "tract": community["fips_tract"],
                "county": base["county"],
                "vulnerability": community["vulnerability_index"],
                "vulnerability_label": vulnerability_label,
                "need_type": need.get("need_type", "unknown"),
                "need_severity": need.get("severity", 0.0),
                "population": community["population"],
                "fill_color": color,
                "radius": 34000,
            }
        )
    return points


def _tract_polygons(communities: list[dict[str, Any]], needs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    polygons = []
    for point in _community_points(communities, needs):
        lat = float(point["lat"])
        lon = float(point["lon"])
        size = 0.16
        polygons.append(
            {
                **point,
                "polygon": [
                    [lon - size, lat - size],
                    [lon + size, lat - size],
                    [lon + size, lat + size],
                    [lon - size, lat + size],
                ],
            }
        )
    return polygons


def _match_cards(matches: list[dict[str, Any]], resources: dict[str, dict[str, Any]], needs: dict[str, dict[str, Any]]) -> None:
    for match in matches:
        resource = resources.get(match["resource_id"], {})
        need = needs.get(match["need_id"], {})
        with st.container(border=True):
            st.markdown(f"**Equity Score:** {match['equity_score']}")
            st.markdown(f"**Resource:** {resource.get('subtype', match['resource_id'])}")
            st.markdown(f"**Need:** {need.get('need_type', match['need_id'])}")
            st.markdown(f"**Status:** {match['status'].title()}")
            routing = match.get("routing_plan") or {}
            st.caption(
                f"Route: {routing.get('origin', 'Pending')} -> "
                f"{routing.get('destination', 'Pending')} | "
                f"ETA {routing.get('eta_hours', 'TBD')}h"
            )

            action_columns = st.columns(3)
            for label, action, column in (
                ("Accept", "accept", action_columns[0]),
                ("Modify", "modify", action_columns[1]),
                ("Skip", "skip", action_columns[2]),
            ):
                if column.button(label, key=f"{match['match_id']}-{action}", use_container_width=True):
                    try:
                        _post_json(f"/api/matches/{match['match_id']}/decision", {"decision": action})
                        st.session_state["flash_message"] = f"Match {match['match_id']} updated to {action}."
                    except requests.RequestException as error:
                        st.session_state["flash_message"] = f"Decision failed: {error}. Check the backend is running at {BACKEND_URL} and try again."
                    st.rerun()


def main() -> None:
    st.title("ReliefLink")
    st.caption("Disaster relief resource matching with equity-first routing.")

    top_columns = st.columns([1, 4])
    if top_columns[0].button("Run Pipeline", type="primary", use_container_width=True):
        with st.spinner("Running SequentialAgent -> ParallelAgent -> LoopAgent pipeline..."):
            try:
                job = _post_json("/api/run-pipeline")
                st.session_state["flash_message"] = f"Pipeline complete: {job['status']} ({job['iterations_run']} iterations)."
            except requests.RequestException as error:
                st.session_state["flash_message"] = f"Pipeline failed: {error}. Ensure GOOGLE_API_KEY is set and the backend is reachable at {BACKEND_URL}."
        time.sleep(0.5)
        st.rerun()

    if "flash_message" in st.session_state:
        st.info(st.session_state["flash_message"])

    try:
        payload = _get_json("/api/matches")
    except requests.RequestException as error:
        st.error(f"Unable to reach backend at {BACKEND_URL}: {error}")
        st.stop()

    agencies = {agency["agency_id"]: agency["name"] for agency in payload.get("agencies", [])}
    resources = payload.get("resources", [])
    communities = payload.get("communities", [])
    needs = payload.get("needs", [])
    matches = payload.get("matches", [])

    top_summary = st.columns(4)
    top_summary[0].metric("Resources", payload["summary"]["total_resources"])
    top_summary[1].metric("Needs", payload["summary"]["total_needs"])
    top_summary[2].metric("Matches", payload["summary"]["matched"])
    top_summary[3].metric("Pending Decisions", payload["summary"]["pending"])

    left_panel, center_panel, right_panel = st.columns([1.2, 1.4, 1.2], gap="large")

    with left_panel:
        st.subheader("Resource Inventory")
        resource_table = _resources_table(resources, agencies)
        if resource_table.empty:
            st.warning("Run the pipeline to populate inventory.")
        else:
            st.dataframe(resource_table, use_container_width=True, hide_index=True)

    with center_panel:
        st.subheader("Needs Map + SVI Heat")
        tract_polygons = _tract_polygons(communities, needs)
        if not tract_polygons:
            st.warning("Run the pipeline to render Florida tract needs.")
        else:
            deck = pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=pdk.ViewState(latitude=27.8, longitude=-82.5, zoom=6.3, pitch=0),
                tooltip={
                    "html": (
                        "<b>Tract:</b> {tract}<br/>"
                        "<b>County:</b> {county}<br/>"
                        "<b>Vulnerability:</b> {vulnerability} ({vulnerability_label})<br/>"
                        "<b>Need:</b> {need_type}<br/>"
                        "<b>Need Severity:</b> {need_severity}<br/>"
                        "<b>Population:</b> {population}"
                    )
                },
                layers=[
                    pdk.Layer(
                        "PolygonLayer",
                        data=tract_polygons,
                        get_polygon="polygon",
                        get_fill_color="fill_color",
                        pickable=True,
                        stroked=True,
                        get_line_color=[55, 55, 55],
                        line_width_min_pixels=1,
                        filled=True,
                        opacity=0.5,
                    )
                ],
            )
            st.pydeck_chart(deck, use_container_width=True)
            st.markdown("**Accessibility Legend**")
            st.markdown("Low vulnerability: green tract fill + text label `Low`")
            st.markdown("Medium vulnerability: yellow tract fill + text label `Medium`")
            st.markdown("High vulnerability: red tract fill + text label `High`")

    with right_panel:
        st.subheader("Match List")
        if not matches:
            st.warning("Run the pipeline to generate match recommendations.")
        else:
            resource_index = {resource["resource_id"]: resource for resource in resources}
            need_index = {need["need_id"]: need for need in needs}
            _match_cards(matches, resource_index, need_index)


if __name__ == "__main__":
    main()
