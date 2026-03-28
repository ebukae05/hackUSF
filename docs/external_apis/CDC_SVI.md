# CDC Social Vulnerability Index (SVI) — Reference

## What is SVI?

The Social Vulnerability Index ranks every US census tract on 16 social factors grouped into 4 themes. Score ranges from 0 (lowest vulnerability) to 1 (highest vulnerability) using percentile ranking.

A census tract with SVI score 0.85 means it is more vulnerable than 85% of all other tracts.

## Data Access

- **Interactive Map:** https://www.atsdr.cdc.gov/place-health/php/svi/svi-interactive-map.html
- **Data Downloads:** https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
- **Available years:** 2000, 2010, 2014, 2016, 2018, 2020, 2022
- **Formats:** CSV, Shapefile (for GIS)
- **Geographic levels:** Census tract (primary), County

**No API key required.** Data is downloadable as CSV files.

> **VERIFIED 2026-03-28:**
> - Working download URL: `https://svi.cdc.gov/Documents/Data/2022/csv/states/SVI_2022_US.csv` (58MB)
> - CSV has 158 columns. All key columns verified present.
> - Census Geocoder API works for address → FIPS tract lookup.

## The 4 Vulnerability Themes

### Theme 1: Socioeconomic Status
- Below 150% poverty
- Unemployed (civilian, 16+)
- Housing cost burden
- No high school diploma (25+)
- No health insurance

### Theme 2: Household Characteristics
- Aged 65 and older
- Aged 17 and younger
- Civilian with a disability (5+)
- Single-parent households
- English language proficiency

### Theme 3: Racial & Ethnic Minority Status
- Hispanic or Latino
- Black/African American
- American Indian/Alaska Native
- Asian
- Native Hawaiian/Pacific Islander
- Two or more races
- Other race

### Theme 4: Housing Type & Transportation
- Multi-unit structures (10+ units)
- Mobile homes
- Crowding (more people than rooms)
- No vehicle access
- Group quarters (institutional)

---

## Key Column Names (2020/2022 data)

| Column | Description |
|---|---|
| `FIPS` | Census tract FIPS code (unique ID) |
| `STATE` | State name |
| `ST_ABBR` | State abbreviation |
| `STCNTY` | State + County FIPS |
| `COUNTY` | County name |
| `LOCATION` | Tract description |
| `E_TOTPOP` | Total population estimate |
| `RPL_THEMES` | **Overall SVI score (0-1)** — the main number you want |
| `RPL_THEME1` | Theme 1 percentile (socioeconomic) |
| `RPL_THEME2` | Theme 2 percentile (household characteristics) |
| `RPL_THEME3` | Theme 3 percentile (racial/ethnic minority) |
| `RPL_THEME4` | Theme 4 percentile (housing/transportation) |
| `SPL_THEMES` | Sum of series percentiles (raw score before percentile) |
| `F_THEMES` | Count of flags (number of variables in 90th percentile) |
| `E_POV150` | Estimated persons below 150% poverty |
| `E_UNEMP` | Estimated unemployed |
| `E_NOHSDP` | Estimated no high school diploma |
| `E_UNINSUR` | Estimated uninsured |
| `E_AGE65` | Estimated aged 65+ |
| `E_AGE17` | Estimated aged 17 and under |
| `E_DISABL` | Estimated with disability |
| `E_SNGPNT` | Estimated single-parent households |
| `E_MOBILE` | Estimated mobile homes |
| `E_NOVEH` | Estimated no vehicle |

**RPL_ columns are percentile rankings (0-1). These are what you use for equity scoring.**

---

## Python Examples

### Load SVI data and find vulnerable tracts in Tampa Bay

```python
import pandas as pd

# Verified working download URL (58MB):
# https://svi.cdc.gov/Documents/Data/2022/csv/states/SVI_2022_US.csv
svi = pd.read_csv("SVI_2022_US.csv")

# Filter to Florida
fl_svi = svi[svi["ST_ABBR"] == "FL"]

# Filter to Tampa Bay counties (Hillsborough, Pinellas, Pasco, Manatee)
tampa_counties = ["Hillsborough", "Pinellas", "Pasco", "Manatee"]
tampa_svi = fl_svi[fl_svi["COUNTY"].isin(tampa_counties)]

# Sort by overall vulnerability (highest = most vulnerable)
most_vulnerable = tampa_svi.sort_values("RPL_THEMES", ascending=False)

print("Top 10 most vulnerable census tracts in Tampa Bay:")
for _, row in most_vulnerable.head(10).iterrows():
    print(f"  FIPS: {row['FIPS']}")
    print(f"  County: {row['COUNTY']}")
    print(f"  Population: {row['E_TOTPOP']:,.0f}")
    print(f"  Overall SVI: {row['RPL_THEMES']:.4f}")
    print(f"  Socioeconomic: {row['RPL_THEME1']:.4f}")
    print(f"  Household: {row['RPL_THEME2']:.4f}")
    print(f"  Minority: {row['RPL_THEME3']:.4f}")
    print(f"  Housing/Transport: {row['RPL_THEME4']:.4f}")
    print()
```

### Create vulnerability score for equity routing

```python
def get_vulnerability_score(fips_code: str, svi_data: pd.DataFrame) -> dict:
    """Look up vulnerability score for a census tract."""
    tract = svi_data[svi_data["FIPS"] == fips_code]
    if tract.empty:
        return {"error": f"No data for FIPS {fips_code}"}

    row = tract.iloc[0]
    return {
        "fips": fips_code,
        "county": row["COUNTY"],
        "population": int(row["E_TOTPOP"]),
        "overall_svi": round(float(row["RPL_THEMES"]), 4),
        "socioeconomic": round(float(row["RPL_THEME1"]), 4),
        "household": round(float(row["RPL_THEME2"]), 4),
        "minority": round(float(row["RPL_THEME3"]), 4),
        "housing_transport": round(float(row["RPL_THEME4"]), 4),
        "vulnerability_class": (
            "Very High" if row["RPL_THEMES"] >= 0.75 else
            "High" if row["RPL_THEMES"] >= 0.50 else
            "Moderate" if row["RPL_THEMES"] >= 0.25 else
            "Low"
        )
    }
```

### Map FIPS to zip code (approximate)

CDC SVI uses census tracts (FIPS), not zip codes. For zip-to-tract mapping:

```python
# HUD USPS ZIP-Tract crosswalk: https://www.huduser.gov/portal/datasets/usps_crosswalk.html
# Or use Census Geocoder API to convert address → tract

import requests

def address_to_tract(address: str) -> str:
    """Convert address to census tract FIPS using Census Geocoder."""
    url = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json"
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    matches = data.get("result", {}).get("addressMatches", [])
    if matches:
        geographies = matches[0].get("geographies", {})
        tracts = geographies.get("Census Tracts", [])
        if tracts:
            return tracts[0]["GEOID"]  # This is the FIPS code
    return None
```

---

## How to Use SVI for ReliefLink Equity Routing

1. **Load SVI data** for the disaster-affected region
2. **For each community/tract in the disaster footprint**, look up `RPL_THEMES` (overall vulnerability)
3. **Rank communities** by vulnerability score (highest first)
4. **Route resources** to highest-vulnerability tracts first
5. **Display** vulnerability scores on the dashboard as color-coded heat map

**Equity formula:**
```
Priority Score = (Need Severity × 0.5) + (SVI Score × 0.3) + (Distance to Nearest Resource × 0.2)
```

Communities with higher priority scores get resources first.
