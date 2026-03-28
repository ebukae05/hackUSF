# NOAA National Weather Service API — Reference

## Base URL

```
https://api.weather.gov
```

## Required Headers

```
User-Agent: (relieflink-hackathon, contact@example.com)
Accept: application/geo+json
```

The `User-Agent` header is **recommended** (docs say required, but API returns 200 without it). Include it anyway to avoid rate limiting.

## Authentication

**None required.** Free, open API.

## Rate Limits

No published hard limit. "Allows a generous amount for typical use." If exceeded, retry after ~5 seconds.

## Response Format

Default: GeoJSON. All timestamps in ISO-8601.

---

## Key Endpoints

### 1. Active Alerts (most important for disaster monitoring)

**All active alerts:**
```
GET https://api.weather.gov/alerts/active
```

**By state:**
```
GET https://api.weather.gov/alerts/active?area=FL
```

**By severity:**
```
GET https://api.weather.gov/alerts/active?severity=Extreme,Severe
```

**Alert types list:**
```
GET https://api.weather.gov/alerts/types
```

**Filter parameters:**
- `area` — state abbreviation (e.g. `FL`, `TX`)
- `zone` — UGC zone code
- `severity` — `Extreme`, `Severe`, `Moderate`, `Minor`, `Unknown`
- `status` — `actual`, `exercise`, `system`, `test`
- `event` — event type string (e.g. `Hurricane Warning`, `Flood Watch`)

**Response fields:**
```json
{
  "features": [
    {
      "properties": {
        "id": "alert-id",
        "areaDesc": "Hillsborough County, FL",
        "severity": "Extreme",
        "certainty": "Observed",
        "urgency": "Immediate",
        "event": "Hurricane Warning",
        "headline": "Hurricane Warning issued...",
        "description": "Full text description...",
        "instruction": "Take shelter immediately...",
        "onset": "2026-03-28T12:00:00-04:00",
        "expires": "2026-03-29T12:00:00-04:00",
        "affectedZones": ["https://api.weather.gov/zones/forecast/FLZ050"]
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lon, lat], ...]]
      }
    }
  ]
}
```

### 2. Points (Location Lookup)

```
GET https://api.weather.gov/points/{lat},{lon}
```

**Example (Tampa Bay):**
```
GET https://api.weather.gov/points/27.9506,-82.4572
```

> **VERIFIED 2026-03-28:** Returns office `TBW`, grid `71,98`, county `FLC057`.
> Forecast URL: `https://api.weather.gov/gridpoints/TBW/71,98/forecast`

### 3. Forecast

```
GET https://api.weather.gov/gridpoints/{office}/{gridX},{gridY}/forecast
```

Returns 12-hour forecast periods for 7 days.

### 4. Stations & Observations

```
GET https://api.weather.gov/stations/{stationId}/observations/latest
```

Returns current conditions (temperature, wind, etc.)

### 5. Zones

```
GET https://api.weather.gov/zones/{type}/{zoneId}/forecast
```

---

## Python Examples

### Fetch active Florida alerts

```python
import requests

headers = {
    "User-Agent": "(ReliefLink, hackathon@example.com)",
    "Accept": "application/geo+json"
}

# All active alerts for Florida
resp = requests.get(
    "https://api.weather.gov/alerts/active?area=FL",
    headers=headers
)
alerts = resp.json()

for feature in alerts.get("features", []):
    props = feature["properties"]
    print(f"[{props['severity']}] {props['event']}: {props['headline']}")
    print(f"  Area: {props['areaDesc']}")
    print(f"  Urgency: {props['urgency']}")
    print()
```

### Fetch severe/extreme alerts only

```python
resp = requests.get(
    "https://api.weather.gov/alerts/active?area=FL&severity=Extreme,Severe",
    headers=headers
)
```

### Get forecast for Tampa Bay

```python
# Step 1: Get grid info for Tampa coordinates
point_resp = requests.get(
    "https://api.weather.gov/points/27.9506,-82.4572",
    headers=headers
)
point_data = point_resp.json()
forecast_url = point_data["properties"]["forecast"]

# Step 2: Get forecast
forecast_resp = requests.get(forecast_url, headers=headers)
forecast = forecast_resp.json()

for period in forecast["properties"]["periods"][:4]:
    print(f"{period['name']}: {period['detailedForecast']}")
```

---

## Relevant Alert Event Types for Disaster Response

- `Hurricane Warning` / `Hurricane Watch`
- `Tropical Storm Warning` / `Tropical Storm Watch`
- `Storm Surge Warning` / `Storm Surge Watch`
- `Flood Warning` / `Flash Flood Warning`
- `Tornado Warning` / `Tornado Watch`
- `Severe Thunderstorm Warning`
- `Extreme Wind Warning`
- `Evacuation - Immediate`
