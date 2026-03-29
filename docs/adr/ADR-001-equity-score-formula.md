# ADR-001: Equity Score Formula

**Status:** Accepted
**Date:** 2026-03-28
**Deciders:** ReliefLink team
**Reference:** SYSTEM_DESIGN.md Section 1.3.H (MDR-03)

---

## Context

ReliefLink must rank disaster relief resource allocations so that vulnerable communities receive aid first. Two competing signals exist:

- **Need severity** — how urgent is the disaster impact on this community?
- **Community vulnerability** — how structurally disadvantaged is this community (CDC SVI)?

A weighting decision is required that directly determines which communities receive resources first.

## Decision

Equity score is computed as:

```
equity_score = (vulnerability_index × 0.6) + (need_severity_normalized × 0.4)
```

Where:
- `vulnerability_index` = CDC SVI `RPL_THEMES` (0–1 percentile, 1 = most vulnerable)
- `need_severity_normalized` = `need_severity / 10.0` (normalizes 0–10 to 0–1)
- Vulnerability weight = **0.6** (configurable parameter, default 0.6)
- Severity weight = **0.4** (= 1 − vulnerability_weight)

Implemented in `services/relieflink_agents/models.py` → `compute_equity_score()`.

## Alternatives Considered

| Option | Weights | Rationale for rejection |
|---|---|---|
| Equal weighting (50/50) | vuln×0.5 + sev×0.5 | Does not sufficiently prioritize vulnerable communities; reproduces status quo |
| Pure vulnerability ranking | vuln×1.0 | Ignores actual disaster impact severity; wealthy area with low SVI could have catastrophic need |
| Three-factor (severity, SVI, proximity) | sev×0.5 + SVI×0.3 + proximity×0.2 | Proximity advantage reinforces existing infrastructure bias; excluded per equity-first premise |
| Multi-criteria Pareto optimization | — | Too complex for 4-minute demo; harder to explain to judges |

## Rationale

Vulnerability must dominate the ranking to fulfill the equity-first premise:

> *"The Cantillon Effect in disaster response means those closest to relief infrastructure receive aid first, while those most in need wait longest. ReliefLink inverts this by making vulnerability the primary sorting criterion."*

A 60/40 split gives vulnerability clear primacy while ensuring communities with catastrophic need severity are not deprioritized solely because their baseline SVI is moderate.

## Consequences

- Communities with higher CDC SVI scores receive resources first even if their immediate need severity is slightly lower than a less-vulnerable community.
- The `vulnerability_weight` parameter is configurable — operators or future releases can adjust the split without changing the formula structure.
- The formula is deterministic, auditable, and explainable to emergency management operators.

## Invalidating Evidence

Domain experts (emergency managers) rejecting the weighting as unrealistic or counterproductive would trigger re-evaluation of this decision.
