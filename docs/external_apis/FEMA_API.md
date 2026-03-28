# FEMA OpenFEMA API — Reference

## Base URL

```
https://www.fema.gov/api/open/v2/
```

## Authentication

**None required.** Free, open API. No API key needed.

## Rate Limits

1000 records per request (use pagination for more). No published rate limit.

## Response Format

JSON by default. Supports CSV via `$format=csv`.

---

## Key Datasets

| Dataset | Endpoint | Description |
|---|---|---|
| Disaster Declarations | `/DisasterDeclarationsSummaries` | All declared disasters with type, date, state, programs |
| ~~FEMA Web Disaster Summaries~~ | ~~`/FemaWebDisasterSummaries`~~ | **DOES NOT EXIST on v2 API.** Use DisasterDeclarationsSummaries with program fields. |
| Housing Assistance (IA) | `/HousingAssistanceOwners` | Individual assistance to homeowners |
| Public Assistance Projects | `/PublicAssistanceFundedProjectsDetails` | Infrastructure/public projects funded |
| Registration Intake | `/RegistrationIntakeIndividualsHouseholdPrograms` | Individual registrations for assistance |
| Hazard Mitigation Grants | `/HazardMitigationGrantProgramPropertyAcquisitions` | Mitigation project data |
| NFIP Claims | `/FimaNfipClaims` | Flood insurance claims |
| NFIP Policies | `/FimaNfipPolicies` | Flood insurance policies |

Full list: https://www.fema.gov/about/openfema/data-sets

---

## Query Parameters (OData syntax)

| Parameter | Description | Example |
|---|---|---|
| `$filter` | Filter results | `$filter=state eq 'FL'` (uses state abbreviation, NOT full name) |
| `$select` | Choose specific fields | `$select=disasterNumber,state,declarationDate` |
| `$orderby` | Sort results | `$orderby=declarationDate desc` |
| `$top` | Limit number of results | `$top=10` |
| `$skip` | Skip N results (pagination) | `$skip=100` |
| `$inlinecount` | Include total count | `$inlinecount=allpages` |
| `$format` | Response format | `$format=csv` |

### Filter operators
- `eq` — equals: `state eq 'Florida'`
- `ne` — not equals
- `gt`, `ge`, `lt`, `le` — comparisons
- `and`, `or` — logical
- `contains()` — substring: `contains(declarationTitle, 'Hurricane')`
- `startswith()`, `endswith()`

---

## Key Endpoints

### 1. Disaster Declarations (most important)

```
GET https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries
```

**Key fields:**
- `disasterNumber` — unique disaster ID (e.g. 4673)
- `state` — state name
- `declarationType` — DR (major disaster), EM (emergency), FM (fire management)
- `declarationDate` — ISO date of declaration
- `incidentType` — Hurricane, Flood, Severe Storm, Fire, etc.
- `declarationTitle` — e.g. "HURRICANE IAN"
- `ihProgramDeclared` — Individual & Household program active (true/false)
- `iaProgramDeclared` — Individual Assistance active
- `paProgramDeclared` — Public Assistance active
- `hmProgramDeclared` — Hazard Mitigation active
- `designatedArea` — county/area name
- `placeCode` — FIPS code
- `incidentBeginDate` / `incidentEndDate`

### 2. Disaster Summaries

```
GET https://www.fema.gov/api/open/v2/FemaWebDisasterSummaries
```

**Key fields:**
- `totalAmountIhpApproved` — total individual assistance approved ($)
- `totalAmountHaApproved` — housing assistance approved ($)
- `totalAmountOnaApproved` — other needs assistance approved ($)
- `totalNumberIaApproved` — number of IA applications approved

### 3. Housing Assistance

```
GET https://www.fema.gov/api/open/v2/HousingAssistanceOwners
```

Individual household-level assistance data.

### 4. NFIP Flood Claims

```
GET https://www.fema.gov/api/open/v2/FimaNfipClaims
```

Flood insurance claim data — useful for understanding flood impact patterns.

---

## Python Examples

### Recent Florida disaster declarations

> **VERIFIED 2026-03-28:** `state` field uses **abbreviation** (e.g. `'FL'`), NOT full name.

```python
import requests

url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
params = {
    "$filter": "state eq 'FL'",  # MUST use abbreviation, not 'Florida'
    "$orderby": "declarationDate desc",
    "$top": 10,
    "$select": "disasterNumber,declarationTitle,declarationType,declarationDate,incidentType,designatedArea"
}

resp = requests.get(url, params=params)
data = resp.json()

for disaster in data.get("DisasterDeclarationsSummaries", []):
    print(f"#{disaster['disasterNumber']} {disaster['declarationTitle']}")
    print(f"  Type: {disaster['incidentType']}")
    print(f"  Date: {disaster['declarationDate']}")
    print(f"  Area: {disaster['designatedArea']}")
    print()
```

### Hurricane declarations only

```python
params = {
    "$filter": "state eq 'FL' and incidentType eq 'Hurricane'",  # abbreviation!
    "$orderby": "declarationDate desc",
    "$top": 20
}
resp = requests.get(url, params=params)
# Verified: returns Hurricane Milton (4844) etc.
```

### Get program data for a specific disaster

> **NOTE:** `FemaWebDisasterSummaries` endpoint does NOT exist on v2 API. Use `DisasterDeclarationsSummaries` with program fields instead.

```python
disaster_num = 4844  # Hurricane Milton
params = {
    "$filter": f"disasterNumber eq {disaster_num}",
    "$select": "disasterNumber,declarationTitle,designatedArea,ihProgramDeclared,iaProgramDeclared,paProgramDeclared,hmProgramDeclared"
}
resp = requests.get(url, params=params)
data = resp.json()

for d in data.get("DisasterDeclarationsSummaries", []):
    print(f"#{d['disasterNumber']} {d['declarationTitle']} — {d['designatedArea']}")
    print(f"  Individual & Household: {d['ihProgramDeclared']}")
    print(f"  Individual Assistance: {d['iaProgramDeclared']}")
    print(f"  Public Assistance: {d['paProgramDeclared']}")
    print(f"  Hazard Mitigation: {d['hmProgramDeclared']}")
```

### Pagination (get all results)

```python
all_results = []
skip = 0
top = 1000

while True:
    params = {
        "$filter": "state eq 'Florida' and incidentType eq 'Hurricane'",
        "$top": top,
        "$skip": skip,
        "$orderby": "declarationDate desc"
    }
    resp = requests.get(url, params=params)
    batch = resp.json().get("DisasterDeclarationsSummaries", [])
    if not batch:
        break
    all_results.extend(batch)
    skip += top

print(f"Total records: {len(all_results)}")
```

---

## Relevant Incident Types for ReliefLink

- `Hurricane`
- `Flood`
- `Severe Storm(s)`
- `Tornado`
- `Coastal Storm`
- `Typhoon`
- `Tropical Storm`
- `Dam/Levee Break`
