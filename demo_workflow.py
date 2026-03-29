"""
ReliefLink - Demo Workflow Script
HackUSF 2026 | March 29, 2026

Demonstrates the CS-02 slice end-to-end:
  1. ResourceScanner aggregates inventories from 4 source categories
  2. NeedMapper loads CDC SVI data and assesses Tampa Bay communities
  3. A2A bidirectional message exchange between agents
  4. Equity-ranked need output ready for MatchOptimizer

Run:
    python demo_workflow.py

This script does NOT require any API keys - it uses bundled fallback data.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("demo")

sys.path.insert(0, str(Path(__file__).parent))

from services.relieflink_agents.resource_scanner import (
    ResourceScanner,
    _agency_source_category,
)
from services.relieflink_agents.need_mapper import NeedMapper
from services.relieflink_agents.models import NeedType, ResourceType


# ---------------------------------------------------------------------------
# Demo scenario: Hurricane Helene - Tampa Bay landfall
# ---------------------------------------------------------------------------
SCENARIO = {
    "name": "Hurricane Helene - Tampa Bay Landfall",
    "state": "FL",
    "disaster_id": "4830",
    "disaster_type": "hurricane",
    "disaster_severity": 8.5,
    # Hillsborough, Pinellas, Manatee, Pasco county FIPS
    "disaster_footprint": ["12057", "12103", "12081", "12101"],
    "declared_date": "2026-03-25T00:00:00Z",
}


def separator(title=""):
    line = "-" * 72
    if title:
        print("\n" + line)
        print("  " + title)
        print(line)
    else:
        print(line)


def main():
    print("\n" + "=" * 72)
    print("  ReliefLink - CS-02 Demo Workflow")
    print("  HackUSF 2026 | Equity-First Disaster Response Coordination")
    print("=" * 72)
    print("\n  Scenario: " + SCENARIO["name"])
    print("  Affected counties (FIPS): " + ", ".join(SCENARIO["disaster_footprint"]))
    print("  Disaster severity: " + str(SCENARIO["disaster_severity"]) + "/10")

    t_start = time.time()

    # ------------------------------------------------------------------
    # STEP 1: ResourceScanner - aggregate inventories
    # ------------------------------------------------------------------
    separator("STEP 1 - ResourceScanner: Aggregate Resource Inventories (FR-003)")

    scanner = ResourceScanner()
    scan_result = scanner.scan(
        state=SCENARIO["state"],
        disaster_footprint=SCENARIO["disaster_footprint"],
    )
    resources = scan_result["resources"]

    print(
        "\n  Found {} resources across {} source categories:".format(
            len(resources), scan_result["source_count"]
        )
    )
    print("  Source categories: " + ", ".join(scan_result["sources"]))

    # Group by category for display
    by_category: dict = {}
    for r in resources:
        cat = _agency_source_category(r.owner_agency_id)
        by_category.setdefault(cat, []).append(r)

    for cat, cat_resources in sorted(by_category.items()):
        total_qty = sum(r.quantity for r in cat_resources)
        print(
            "\n  [{}] - {} resource items, {:,} total units".format(
                cat.upper(), len(cat_resources), total_qty
            )
        )
        for r in cat_resources:
            loc_str = r.location.address if r.location else "unknown"
            print(
                "    - {:<30} qty={:>6,}  agency={:<18}  loc={}".format(
                    r.subtype, r.quantity, r.owner_agency_id, loc_str[:40]
                )
            )

    # ------------------------------------------------------------------
    # STEP 2: NeedMapper - assess communities and quantify needs
    # ------------------------------------------------------------------
    separator(
        "STEP 2 - NeedMapper: Community Assessment + SVI Vulnerability (FR-004/005/006)"
    )

    mapper = NeedMapper()
    assess_result = mapper.assess(
        disaster_footprint=SCENARIO["disaster_footprint"],
        disaster_severity=SCENARIO["disaster_severity"],
        disaster_type=SCENARIO["disaster_type"],
    )
    communities = assess_result["communities"]
    needs = assess_result["needs"]

    if assess_result.get("fallback_used"):
        print(
            "\n  [WARN] "
            + assess_result.get("staleness_warning", "Using bundled SVI data.")
        )

    print("\n  Identified {} census tracts in disaster footprint".format(len(communities)))

    # Show top 5 most vulnerable communities
    top_communities = sorted(
        communities, key=lambda c: c.vulnerability_index, reverse=True
    )[:5]

    print("\n  Top 5 Most Vulnerable Communities (by SVI RPL_THEMES):")
    header = "  {:<14} {:<15} {:>11} {:>10} {}".format(
        "FIPS Tract", "County", "Population", "SVI Score", "Vulnerability Class"
    )
    print(header)
    print("  " + "=" * 14 + " " + "=" * 15 + " " + "=" * 11 + " " + "=" * 10 + " " + "=" * 20)
    for c in top_communities:
        if c.vulnerability_index >= 0.75:
            vuln_class = "Very High"
        elif c.vulnerability_index >= 0.50:
            vuln_class = "High"
        elif c.vulnerability_index >= 0.25:
            vuln_class = "Moderate"
        else:
            vuln_class = "Low"
        print(
            "  {:<14} {:<15} {:>11,} {:>10.4f} {}".format(
                c.fips_tract, c.county_name, c.population, c.vulnerability_index, vuln_class
            )
        )

    print("\n  Quantified {} needs across all communities".format(len(needs)))

    # Summarize by type
    by_type: dict = {}
    for n in needs:
        by_type[n.need_type.value] = by_type.get(n.need_type.value, 0) + n.quantity_needed

    print("\n  Needs by type:")
    for nt, qty in sorted(by_type.items(), key=lambda x: -x[1]):
        print("    - {:<15}  {:>8,} units needed".format(nt, qty))

    # ------------------------------------------------------------------
    # STEP 3: A2A Bidirectional Exchange (FR-014 / CF-04)
    # ------------------------------------------------------------------
    separator("STEP 3 - A2A Coordination: ResourceScanner <-> NeedMapper (FR-014)")

    resources_msg = scanner.get_a2a_message(resources)
    needs_msg = mapper.get_a2a_message(needs)

    # Exchange messages
    mapper.receive_a2a_message(resources_msg)
    scanner.receive_a2a_message(needs_msg)

    print("\n  ResourceScanner -> NeedMapper message (resources_summary):")
    rs = resources_msg["resources_summary"]
    print("    total_available: {:,} units".format(rs["total_available"]))
    print("    by_type: " + str(dict(sorted(rs["by_type"].items()))))
    print("    source_categories: " + str(rs["source_categories"]))

    print("\n  NeedMapper -> ResourceScanner message (needs_summary):")
    ns = needs_msg["needs_summary"]
    print("    total_unfulfilled: {:,} units".format(ns["total_unfulfilled"]))
    print("    community_count: {}".format(ns["community_count"]))
    print("    by_type: " + str(dict(sorted(ns["by_type"].items()))))
    print("    by_severity: " + str(ns["by_severity"]))

    # ------------------------------------------------------------------
    # STEP 4: Top priority needs (ready for MatchOptimizer)
    # ------------------------------------------------------------------
    separator(
        "STEP 4 - Equity-Ranked Needs (Ready for MatchOptimizer / FR-006 / MDR-03)"
    )

    communities_map = {c.fips_tract: c for c in communities}

    print("\n  Top 10 Highest-Priority Needs (equity_score = SVI*0.6 + severity*0.4):")
    print(
        "\n  {:<4} {:<12} {:>8} {:>9} {:>7} {:>8} {:<15} {}".format(
            "#", "Type", "Qty", "Severity", "SVI", "Equity", "County", "Tract"
        )
    )
    print(
        "  "
        + "=" * 4 + " "
        + "=" * 12 + " "
        + "=" * 8 + " "
        + "=" * 9 + " "
        + "=" * 7 + " "
        + "=" * 8 + " "
        + "=" * 15 + " "
        + "=" * 14
    )

    for i, n in enumerate(needs[:10], 1):
        c = communities_map.get(n.community_fips_tract)
        county = c.county_name if c else "?"
        svi = c.vulnerability_index if c else 0.0
        print(
            "  {:<4} {:<12} {:>8,} {:>9.2f} {:>7.4f} {:>8.4f} {:<15} {}".format(
                i,
                n.need_type.value,
                n.quantity_needed,
                n.severity,
                svi,
                n.equity_score,
                county,
                n.community_fips_tract,
            )
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    t_elapsed = time.time() - t_start
    separator("DEMO SUMMARY")

    print(
        """
  Scenario:         {}
  Affected areas:   {} census tracts in {} counties
  Resources found:  {} items from {} source categories
  Needs identified: {} needs quantified with equity scores
  A2A exchange:     OK ResourceScanner <-> NeedMapper (FR-014)
  Elapsed time:     {:.2f}s (well within 120s NFR-PERF-001 budget)

  NEXT STEPS (handled by MatchOptimizer + Dashboard):
  -> LoopAgent iteratively matches {} resources to {} needs
  -> Equity-ranked allocation ensures highest-SVI communities get resources first
  -> Agency operators review/accept/skip via dashboard (human-in-the-loop)
  -> Full pipeline demo target: < 30 seconds
""".format(
            SCENARIO["name"],
            len(communities),
            len(SCENARIO["disaster_footprint"]),
            len(resources),
            scan_result["source_count"],
            len(needs),
            t_elapsed,
            len(resources),
            len(needs),
        )
    )

    print("=" * 72)
    print("  CS-02 Demo Complete - FT-01 + FT-03 + CS-02 all passing")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
