"""
NeedMapper Agent - CS-02 (B4)

Cross-references disaster footprint with CDC SVI census-tract data to:
  1. Identify affected communities and compute vulnerability scores (RPL_THEMES)
  2. Quantify needs (shelter, supplies, medical, evacuation) with severity scores
  3. Compute equity scores: vulnerability_index * 0.6 + need_severity * 0.4
  4. Participate in A2A communication with ResourceScanner (FR-014 / CF-04)

Fallback: if CDC SVI CSV fails to load, uses bundled fl_svi_subset.csv (FM-03)

FRs: FR-004, FR-005, FR-006, FR-014
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .models import (
    Community,
    Need,
    NeedType,
    SVIThemes,
    compute_equity_score,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_BUNDLED_SVI_PATH = _DATA_DIR / "fl_svi_subset.csv"

# Need severity multipliers by disaster type
_SEVERITY_MULTIPLIERS: Dict[str, float] = {
    "hurricane": 1.0,
    "flood": 0.85,
    "tornado": 0.75,
    "wildfire": 0.80,
    "earthquake": 0.90,
    "other": 0.60,
}

# Need distribution by disaster type: fraction of population needing each type
_NEED_DISTRIBUTION: Dict[str, Dict[str, float]] = {
    "hurricane": {
        "shelter": 0.08,      # 8% of pop needs emergency shelter
        "supplies": 0.25,     # 25% need emergency supplies
        "medical": 0.04,      # 4% need medical assistance
        "evacuation": 0.12,   # 12% need evacuation support
        "equipment": 0.02,
    },
    "flood": {
        "shelter": 0.10,
        "supplies": 0.20,
        "medical": 0.03,
        "evacuation": 0.15,
        "equipment": 0.03,
    },
    "tornado": {
        "shelter": 0.15,
        "supplies": 0.30,
        "medical": 0.06,
        "evacuation": 0.05,
        "equipment": 0.04,
    },
    "wildfire": {
        "shelter": 0.12,
        "supplies": 0.22,
        "medical": 0.03,
        "evacuation": 0.18,
        "equipment": 0.05,
    },
    "other": {
        "shelter": 0.05,
        "supplies": 0.15,
        "medical": 0.03,
        "evacuation": 0.05,
        "equipment": 0.02,
    },
}


# ---------------------------------------------------------------------------
# A2A message shapes (CF-04)
# ---------------------------------------------------------------------------

def build_needs_summary(needs: List[Need]) -> Dict[str, Any]:
    """
    Build the A2A message that NeedMapper sends to ResourceScanner.
    Contract: { "needs_summary": { "by_type": {...}, "by_severity": {...} } }
    """
    by_type: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}  # "high" / "medium" / "low" buckets

    for n in needs:
        type_key = n.need_type.value
        by_type[type_key] = by_type.get(type_key, 0) + n.quantity_needed

        if n.severity >= 7.0:
            bucket = "high"
        elif n.severity >= 4.0:
            bucket = "medium"
        else:
            bucket = "low"
        by_severity[bucket] = by_severity.get(bucket, 0) + 1

    return {
        "needs_summary": {
            "by_type": by_type,
            "by_severity": by_severity,
            "total_unfulfilled": sum(by_type.values()),
            "community_count": len({n.community_fips_tract for n in needs}),
        }
    }


# ---------------------------------------------------------------------------
# SVI data loading
# ---------------------------------------------------------------------------

def _load_svi_data(
    svi_csv_path: Optional[str] = None,
    use_bundled: bool = False,
) -> Tuple[pd.DataFrame, bool]:
    """
    Load CDC SVI data into a pandas DataFrame.

    Priority:
    1. Explicit path (svi_csv_path parameter)
    2. SVI_CSV_PATH env var
    3. Bundled FL subset (fallback, FM-03)

    Returns (dataframe, is_fallback).
    """
    # 1. Explicit path
    if svi_csv_path and not use_bundled:
        try:
            df = pd.read_csv(svi_csv_path, dtype={"FIPS": str, "STCNTY": str})
            logger.info("NeedMapper: loaded SVI data from %s (%d rows)", svi_csv_path, len(df))
            return df, False
        except Exception as exc:
            logger.warning("NeedMapper: failed to load SVI from %s: %s", svi_csv_path, exc)

    # 2. Env var path
    env_path = os.environ.get("SVI_CSV_PATH")
    if env_path and not use_bundled:
        try:
            df = pd.read_csv(env_path, dtype={"FIPS": str, "STCNTY": str})
            logger.info("NeedMapper: loaded SVI data from env SVI_CSV_PATH (%d rows)", len(df))
            return df, False
        except Exception as exc:
            logger.warning("NeedMapper: failed to load SVI from env path %s: %s", env_path, exc)

    # 3. Bundled fallback (FM-03)
    logger.warning(
        "NeedMapper: using bundled FL SVI subset as fallback (FM-03). "
        "Dashboard will show staleness warning."
    )
    try:
        df = pd.read_csv(_BUNDLED_SVI_PATH, dtype={"FIPS": str, "STCNTY": str})
        logger.info("NeedMapper: loaded bundled SVI fallback (%d rows)", len(df))
        return df, True
    except Exception as exc:
        logger.error(
            "NeedMapper: bundled SVI also failed: %s. "
            "Returning empty DataFrame - default vulnerability=0.5 will be used.",
            exc,
        )
        return pd.DataFrame(), True


# ---------------------------------------------------------------------------
# Main NeedMapper logic
# ---------------------------------------------------------------------------

class NeedMapper:
    """
    B4 - NeedMapper Agent.

    Cross-references disaster footprint with CDC SVI data, computes
    vulnerability scores and equity scores, and quantifies community needs.

    Usage (standalone):
        mapper = NeedMapper()
        result = mapper.assess(
            disaster_footprint=["12057", "12103"],
            disaster_severity=8.5,
            disaster_type="hurricane",
        )
        communities = result["communities"]
        needs = result["needs"]
    """

    def __init__(
        self,
        svi_csv_path: Optional[str] = None,
        vulnerability_weight: float = 0.6,
    ):
        self._svi_csv_path = svi_csv_path
        self._vulnerability_weight = vulnerability_weight  # MDR-03 configurable
        self._svi_df: Optional[pd.DataFrame] = None
        self._using_fallback = False
        # Holds the most recent A2A message received from ResourceScanner
        self._received_resources_summary: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # SVI data access (lazy-load, cached)
    # ------------------------------------------------------------------

    def _get_svi_df(self) -> pd.DataFrame:
        if self._svi_df is None:
            self._svi_df, self._using_fallback = _load_svi_data(self._svi_csv_path)
        return self._svi_df

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def assess(
        self,
        disaster_footprint: List[str],
        disaster_severity: float,
        disaster_type: str = "hurricane",
    ) -> Dict[str, Any]:
        """
        Assess communities and quantify needs for the given disaster footprint.

        CF-03 success contract:
          { "communities": [Community, ...], "needs": [Need, ...] }

        disaster_footprint: list of 5-digit FIPS county codes
        disaster_severity:  0-10 float (from DisasterMonitor)
        disaster_type:      "hurricane" | "flood" | etc.
        """
        logger.info(
            "NeedMapper: assessing footprint=%s severity=%.1f type=%s",
            disaster_footprint,
            disaster_severity,
            disaster_type,
        )

        # Early return for empty footprint - nothing to assess
        if not disaster_footprint:
            return {"communities": [], "needs": []}

        svi_df = self._get_svi_df()
        communities = self._identify_communities(svi_df, disaster_footprint)
        needs = self._quantify_needs(communities, disaster_severity, disaster_type)

        logger.info(
            "NeedMapper: identified %d communities, %d needs. fallback=%s",
            len(communities),
            len(needs),
            self._using_fallback,
        )

        result: Dict[str, Any] = {
            "communities": communities,
            "needs": needs,
        }
        if self._using_fallback:
            result["fallback_used"] = True
            result["staleness_warning"] = (
                "Vulnerability data is from bundled dataset. Live CDC data unavailable."
            )

        return result

    def get_a2a_message(self, needs: List[Need]) -> Dict[str, Any]:
        """Build the A2A message to send to ResourceScanner (CF-04)."""
        return build_needs_summary(needs)

    def receive_a2a_message(self, resources_summary: Dict[str, Any]) -> None:
        """
        Receive A2A message from ResourceScanner (CF-04).
        Stores resource context; could be used to refine need severity estimates.
        """
        self._received_resources_summary = resources_summary
        logger.info(
            "NeedMapper A2A: received resource summary from ResourceScanner. "
            "total_available=%s",
            resources_summary.get("resources_summary", {}).get("total_available"),
        )

    # ------------------------------------------------------------------
    # Community identification (FR-004)
    # ------------------------------------------------------------------

    def _identify_communities(
        self, svi_df: pd.DataFrame, disaster_footprint: List[str]
    ) -> List[Community]:
        """
        Cross-reference disaster footprint county FIPS codes with SVI tract data.
        Computes vulnerability_index (RPL_THEMES) per tract. (FR-004)

        Bug fix: work on a local copy of the DataFrame so the cached self._svi_df
        is never mutated by str.zfill() normalization of the STCNTY column.
        """
        communities: List[Community] = []

        if svi_df.empty:
            # No SVI data at all - create placeholder communities with default vulnerability
            logger.warning(
                "NeedMapper: empty SVI DataFrame; assigning default vulnerability=0.5 "
                "to all counties in footprint."
            )
            for county_fips in disaster_footprint:
                communities.append(
                    Community(
                        fips_tract=county_fips + "000000",  # dummy tract
                        county_fips=county_fips,
                        state="FL",
                        population=10000,
                        vulnerability_index=0.5,
                        svi_themes=None,
                        county_name="Unknown",
                    )
                )
            return communities

        # Work on a local copy so the cached DataFrame is never mutated.
        # STCNTY is 5-digit county FIPS (state+county); FIPS is 11-digit tract.
        working = svi_df.copy()
        working["STCNTY"] = working["STCNTY"].astype(str).str.zfill(5)
        affected = working[working["STCNTY"].isin(disaster_footprint)]

        if affected.empty:
            logger.warning(
                "NeedMapper: no SVI tracts found for footprint %s. "
                "Check that STCNTY column contains 5-digit county FIPS codes.",
                disaster_footprint,
            )

        for _, row in affected.iterrows():
            rpl = self._safe_float(row.get("RPL_THEMES"), fallback_negative=0.5)

            # Bug fix: pass fallback_negative=0.5 for theme sub-scores so that
            # CDC's -999 missing-data sentinel maps to 0.5 (neutral), not 0.0
            # (which would incorrectly label the tract as low vulnerability).
            svi_themes = SVIThemes(
                socioeconomic=self._safe_float(
                    row.get("RPL_THEME1"), fallback_negative=0.5
                ),
                household=self._safe_float(
                    row.get("RPL_THEME2"), fallback_negative=0.5
                ),
                minority=self._safe_float(
                    row.get("RPL_THEME3"), fallback_negative=0.5
                ),
                housing_transport=self._safe_float(
                    row.get("RPL_THEME4"), fallback_negative=0.5
                ),
            )

            community = Community(
                fips_tract=str(row.get("FIPS", "")).zfill(11),
                county_fips=str(row.get("STCNTY", "")).zfill(5),
                state=str(row.get("ST_ABBR", "FL")),
                population=int(self._safe_float(row.get("E_TOTPOP"), fallback_negative=0.0)),
                vulnerability_index=rpl,
                svi_themes=svi_themes,
                county_name=str(row.get("COUNTY", "")),
            )
            communities.append(community)

        logger.info(
            "NeedMapper: identified %d census tracts across %d counties",
            len(communities),
            len({c.county_fips for c in communities}),
        )
        return communities

    # ------------------------------------------------------------------
    # Need quantification (FR-005, FR-006)
    # ------------------------------------------------------------------

    def _quantify_needs(
        self,
        communities: List[Community],
        disaster_severity: float,
        disaster_type: str,
    ) -> List[Need]:
        """
        For each community, create Need objects for each need type.
        Severity is computed from disaster impact + population affected.
        Equity score = vulnerability_index * 0.6 + need_severity_normalized * 0.4
        (MDR-03, FR-006)
        """
        needs: List[Need] = []
        disaster_type_key = disaster_type.lower()
        distribution = _NEED_DISTRIBUTION.get(
            disaster_type_key, _NEED_DISTRIBUTION["other"]
        )
        severity_multiplier = _SEVERITY_MULTIPLIERS.get(disaster_type_key, 0.6)

        for community in communities:
            pop = max(community.population, 1)
            vuln = community.vulnerability_index

            for need_type_str, pop_fraction in distribution.items():
                if pop_fraction <= 0:
                    continue

                # Need severity: scaled by disaster severity and community vulnerability.
                # High-SVI tracts face compounding impacts (fewer pre-existing resources).
                base_severity = disaster_severity * severity_multiplier
                # Vulnerability amplification: 1.0 to 1.5 range
                vuln_amplification = 1.0 + (vuln * 0.5)
                need_severity = min(base_severity * vuln_amplification, 10.0)

                quantity = max(int(pop * pop_fraction), 1)

                equity = compute_equity_score(
                    vulnerability_index=vuln,
                    need_severity=need_severity,
                    vulnerability_weight=self._vulnerability_weight,
                )

                need = Need(
                    community_fips_tract=community.fips_tract,
                    need_type=NeedType(need_type_str),
                    severity=round(need_severity, 2),
                    quantity_needed=quantity,
                    quantity_fulfilled=0,
                    equity_score=equity,
                )
                needs.append(need)

        # Sort by equity score descending (highest priority first)
        needs.sort(key=lambda n: n.equity_score, reverse=True)

        if needs:
            logger.info(
                "NeedMapper: quantified %d needs. Top equity=%.4f, median=%.4f",
                len(needs),
                needs[0].equity_score,
                needs[len(needs) // 2].equity_score,
            )
        else:
            logger.info("NeedMapper: quantified 0 needs.")

        return needs

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(value: Any, fallback_negative: float = 0.0) -> float:
        """
        Convert value to float.
        - On conversion error: returns 0.0
        - On negative value (including CDC's -999 missing-data sentinel):
          returns fallback_negative

        Bug fix: renamed second param from 'default' to 'fallback_negative' and
        made it explicit at every call site that uses CDC columns, so -999
        maps to 0.5 (neutral) instead of 0.0 (incorrectly low vulnerability).
        """
        try:
            f = float(value)
            return f if f >= 0 else fallback_negative
        except (TypeError, ValueError):
            return 0.0
