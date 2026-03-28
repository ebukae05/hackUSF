# System Design Document -- ReliefLink

## 1.0 Premise

- **Problem being solved:** When a disaster strikes, resource-to-need matching takes 7-90+ days because every responding agency (FEMA, state EMAs, Red Cross, volunteer organizations) operates in siloed systems with no cross-agency visibility, no automated needs assessment, and no equity-aware prioritization. Wealthy, well-connected areas receive aid first while vulnerable communities wait longest. This coordination gap costs an estimated $600M/year and produces unquantifiable human suffering.
- **Who it is for:** Emergency management agency operators (FEMA regional coordinators, state EMA dispatchers, Red Cross logistics staff, volunteer organization coordinators) who must allocate scarce resources across affected communities during a declared disaster.
- **Desired outcome:** Reduce resource-to-need matching from weeks to minutes; ensure vulnerable communities (as measured by CDC Social Vulnerability Index) are prioritized first, not last; provide cross-agency resource visibility without requiring any agency to abandon its existing systems.
- **What the product/system does:** ReliefLink is a multi-agent coordination layer that sits alongside (not inside) existing agency systems. It ingests real-time disaster data from FEMA and NOAA, cross-references community vulnerability indices from CDC SVI, aggregates resource inventories across federal/state/NGO/volunteer sources, and produces equity-weighted resource-to-need matches with routing plans. Agency operators review and approve matches through a simple dashboard interface.
- **Why it matters:** The Cantillon Effect in disaster response means those closest to relief infrastructure receive aid first, while those most in need wait longest. ReliefLink inverts this by making vulnerability the primary sorting criterion. Every day of delay in disaster response correlates with increased mortality, displacement permanence, and long-term economic damage to affected communities.
- **Upstream source/reference:** IDEA.md, OPERATIONS_LOG.md (Stages -3 through 0.5), 1-Sentence Distillation from Stage 0.

### 1-Sentence Distillation

> Given real-time disaster impact data and multi-agency resource inventories, the system must match available resources to community needs by severity and vulnerability to produce an equitable, prioritized routing plan without bypassing existing agency authority or requiring unified adoption.

---

## 1.0.0 Workflow Profile Selection

- **Selected profile:** `Startup / Greenfield`
- **Rationale:** This is a hackathon project (HackUSF 2026, judging March 29, 2026) with a 4-minute demo window. The team is building from zero with no legacy systems, no existing users, no compliance audit trail, and no production traffic. Enterprise governance, multi-region HA, and deep security hardening are not justified at this stage. The profile emphasizes premise validation, simple architecture, rapid iteration, and only the subset of distributed constraints justified by demo-readiness and real-API integration.

---

## 1.0.0.1 Premise Acceptance / Ethical Intake Gate

- **Worst plausible malicious or abusive use:** An actor could manipulate vulnerability scores or resource inventory data to divert aid toward preferred communities or away from disfavored ones. Mitigation: the system produces recommendations, not autonomous dispatches. A human operator must Accept/Modify/Skip every match. The system cannot bypass FEMA's legal authority or any agency's chain of command.
- **Privacy/autonomy risk introduced by the data model or interaction model:** CDC SVI data is aggregated at the census-tract level (not individual-level). No personal health information, no individual names, no household-level data enters the system. Disaster declarations and weather alerts are public data. Resource inventories are organizational-level, not individual. Privacy risk is low.
- **Sustainability/environmental cost at scale:** The system runs lightweight LLM inference (Gemini 2.5 Flash) and REST API calls. Compute cost is negligible compared to the physical logistics it coordinates. No training or fine-tuning is performed. Environmental cost is minimal.
- **Harmful, addictive, or exploitative behavior risk:** The system is a professional coordination tool for emergency managers, not a consumer product. No engagement optimization, no attention capture, no addictive loops. The equity-weighting algorithm could theoretically produce allocations that operators disagree with, but the human-in-the-loop design ensures operators retain full decision authority.
- **Proceed / Do Not Proceed decision:** **PROCEED.** The system creates net-positive impact by improving disaster response equity. All identified risks are mitigated by the human-in-the-loop design and the use of aggregated public data only.

---

## 1.0.1 Domain Context

### Primary Domain
Emergency management and disaster response coordination -- specifically the resource allocation and logistics coordination phase that occurs after a disaster is declared and before aid reaches affected communities.

### Adjacent Systems / Institutions / Infrastructures
- **FEMA (Federal Emergency Management Agency):** Declares disasters, controls federal disaster funds and resources, operates its own internal coordination systems. ReliefLink cannot bypass FEMA's legal authority under the Stafford Act.
- **State Emergency Management Agencies (EMAs):** Coordinate state-level response, operate their own dispatch and resource tracking systems. Each state EMA has independent authority within its jurisdiction.
- **American Red Cross and NGOs:** Operate shelters, distribute supplies, manage volunteers. Independent organizations with their own resource inventories and deployment authority.
- **Volunteer Organizations Active in Disaster (VOAD):** Informal networks of community groups, faith organizations, and ad-hoc volunteer teams. Resources are poorly tracked and highly dynamic.
- **NOAA / National Weather Service:** Authoritative source for weather alerts, forecasts, and hazard warnings. Provides real-time data via public API.
- **CDC / ATSDR Social Vulnerability Index:** Provides census-tract-level vulnerability scores across 16 variables grouped into 4 themes (socioeconomic status, household characteristics, racial/ethnic minority status, housing type/transportation). Updated every 2 years; current version is 2022.

### Core Domain Vocabulary and Definitions
- **Disaster Declaration:** A formal declaration (presidential or state-level) that triggers the release of emergency funds and resources. The legal prerequisite for federal aid.
- **Social Vulnerability Index (SVI):** A composite score (0-1) from CDC/ATSDR that ranks census tracts by their vulnerability to external stresses on human health. RPL_THEMES is the overall percentile ranking.
- **Resource Staging Area:** A pre-positioned or dynamically established location where resources are gathered before deployment to affected areas.
- **Equity Score:** ReliefLink's composite metric that combines need severity with community vulnerability to produce a prioritization ranking. Higher equity score = higher priority.
- **Match:** A pairing of a specific available resource to an identified community need, including the routing plan and equity justification.

### Domain Actors / External Parties / Ecosystem Boundaries
- **Agency Operators:** The primary users. They review, approve, modify, or reject recommended matches. They have decision authority within their agency's scope.
- **Incident Commanders:** Senior officials who oversee multi-agency response. They do not directly use ReliefLink but their authority hierarchy constrains what operators can approve.
- **Affected Communities:** The beneficiaries. They do not interact with the system directly. Their needs are represented through aggregated data (SVI scores, disaster footprint overlap, reported needs).

### Formal vs. Actual Authority / Control Path
- **Formal authority:** FEMA has legal authority over federal disaster response. State EMAs have authority over state resources. Red Cross operates under a congressional charter for disaster relief.
- **Actual control path:** In practice, resource deployment is controlled by whoever physically possesses the resources and has local logistics capability. A county warehouse manager's cooperation matters more than a federal directive if the warehouse is the only supply point. ReliefLink must produce recommendations that respect formal authority chains while being useful to the people who actually control resource movement.

### Domain Invariants
- A resource cannot be allocated to more than one need simultaneously.
- A community's vulnerability index is a pre-existing condition, not a disaster outcome -- it does not change during a disaster event.
- Agency authority boundaries are non-negotiable: ReliefLink recommends, agencies decide.
- Disaster footprints are geographic and temporal: they have a physical extent and a time of onset.

### Domain-Specific Risks / Failure Consequences
- **Over-allocation:** Matching more resources to a community than it can absorb wastes scarce supplies.
- **Under-allocation of vulnerable communities:** The failure mode ReliefLink exists to prevent.
- **Stale data:** If disaster conditions change faster than the system updates, matches become invalid.
- **False equity:** If SVI data is outdated or inaccurate for the affected area, the equity weighting could misdirect resources.

### Dominant Tradeoffs
- **Speed vs. accuracy:** Faster matching with imperfect data vs. waiting for perfect information.
- **Equity vs. efficiency:** Routing to the most vulnerable community may not be the logistically cheapest path.
- **Autonomy vs. coordination:** Each agency wants control over its own resources, but coordination requires some visibility sharing.

---

## 1.0.2 Reference Architecture

### Applicable Reference Architecture
The system follows the **multi-agent orchestration** pattern common in AI-coordinated decision support systems, combined with the **advisory overlay** pattern used in logistics coordination systems that must respect existing authority structures.

### Common Component Roles and Boundaries
- **Data Ingestion Agents:** Autonomous agents that monitor external data sources and maintain a current picture of the operating environment. They own data freshness but not data authority.
- **Analysis/Scoring Agent:** Transforms raw data into actionable scores (vulnerability indices, need severity, equity weights). Owns the scoring algorithm but not the decision.
- **Optimization Agent:** Takes scored inputs and produces optimal or near-optimal pairings. Owns the matching algorithm and convergence logic.
- **Human-in-the-Loop Interface:** Presents recommendations to operators and captures their decisions. Owns the interaction flow but not the recommendation logic.
- **Orchestration Layer:** Coordinates agent execution order, manages data handoffs between agents, and ensures the pipeline runs to completion.

### Canonical Interaction Patterns
- **Parallel data ingestion → Sequential optimization → Human review:** The standard flow for advisory decision support systems. Data gathering is embarrassingly parallel; optimization is iterative and sequential; human review is the final gate.
- **Agent-to-Agent (A2A) messaging:** Agents share intermediate results to enable coordinated analysis without centralizing all data in one store.

### Typical Failure Points and Resilience Patterns
- External API unavailability (FEMA, NOAA, CDC) -- mitigated by cached last-known-good data.
- Optimization non-convergence -- mitigated by max-iteration bounds.
- Stale data -- mitigated by freshness timestamps on all ingested data.

### Architectural Variants Considered
- **Fully autonomous dispatch (no human-in-the-loop):** Rejected. Violates agency authority constraints and the ethical gate.
- **Centralized data warehouse approach (no agents):** Rejected. The ADK requirement mandates agent architecture; additionally, agents provide better modularity for parallel data ingestion from heterogeneous sources.
- **Event-driven microservices:** Over-engineered for hackathon scope. Agents within a single process provide sufficient modularity.

### Explicit Deviations from Reference Architecture
- The reference pattern typically assumes durable message queues between agents. ReliefLink uses in-process Google ADK agent orchestration (SequentialAgent, ParallelAgent, LoopAgent) instead of distributed messaging, because the system runs as a single deployment unit at hackathon scale.

---

## 1.1 Functional Requirements

| FR_ID | Requirement | Trace Source | Notes |
|---|---|---|---|
| FR-001 | The system shall ingest active disaster declarations from FEMA OpenFEMA API and produce a structured DisasterEvent with geographic footprint, severity, and affected population when a new declaration is detected. | Premise: "real-time disaster impact data"; Verb: Detect | DisasterMonitor agent |
| FR-002 | The system shall ingest active weather alerts from NOAA NWS API for the target geographic area and enrich the DisasterEvent with current hazard conditions. | Premise: "real-time disaster impact data"; Verb: Detect | DisasterMonitor agent |
| FR-003 | The system shall aggregate resource inventories from at least 3 source categories (federal, state/local, NGO/volunteer) and produce a catalogued Resource list with location, quantity, type, and owning agency. | Premise: "multi-agency resource inventories"; Verb: Inventory | ResourceScanner agent |
| FR-004 | The system shall cross-reference the disaster geographic footprint with CDC SVI census-tract data to identify affected communities and compute a vulnerability score (0-1 scale, RPL_THEMES) for each. | Premise: "equity-first routing"; Verb: Assess | NeedMapper agent |
| FR-005 | The system shall quantify each affected community's specific needs (shelter, supplies, medical, evacuation) as a Need object with severity score based on disaster impact and population affected. | Premise: "community needs"; Verb: Assess | NeedMapper agent |
| FR-006 | The system shall compute an equity score for each community by combining need severity and vulnerability index, where higher vulnerability increases priority. | Premise: "serves vulnerable communities first"; Verb: Prioritize | NeedMapper / MatchOptimizer |
| FR-007 | The system shall iteratively match available Resources to identified Needs, weighted by equity score, and produce a prioritized list of Match objects with routing plans. | Premise: "match available resources to community needs"; Verb: Match | MatchOptimizer (LoopAgent) |
| FR-008 | The MatchOptimizer shall re-run matching iterations until allocation quality converges (delta between iterations < threshold) or a maximum iteration count is reached. | Premise: "in minutes instead of weeks"; Verb: Match | LoopAgent convergence logic |
| FR-009 | The system shall present recommended matches to agency operators via a web dashboard showing resource inventory, needs map with vulnerability overlay, and match recommendations with equity scores. | Premise: "without requiring unified adoption"; User Journey step 6 | Frontend dashboard |
| FR-010 | Agency operators shall be able to Accept, Modify, or Skip each recommended match through the dashboard interface. | Premise: "without bypassing existing agency authority"; User Journey step 7 | Human-in-the-loop gate |
| FR-011 | When an operator accepts a match, the system shall mark the matched resource as allocated and the matched need as fulfilled (or partially fulfilled), then re-optimize remaining unmatched resources and needs. | User Journey step 8; Verb: Route | Re-optimization after acceptance |
| FR-012 | The system shall run DisasterMonitor, ResourceScanner, and NeedMapper in parallel using Google ADK ParallelAgent to minimize data ingestion latency. | Hard Constraint: "Must use Google ADK with ParallelAgent"; Agent Architecture | ADK ParallelAgent |
| FR-013 | The system shall use Google ADK LoopAgent to orchestrate iterative match optimization. | Hard Constraint: "Must use Google ADK with LoopAgent"; Agent Architecture | ADK LoopAgent |
| FR-014 | The system shall enable Agent-to-Agent (A2A) communication between ResourceScanner and NeedMapper for coordinated resource-need cross-referencing. | Hard Constraint: "Must use A2A"; Agent Architecture | ADK A2A protocol |
| FR-015 | The system shall orchestrate the full pipeline as SequentialAgent: ParallelAgent (ingestion) followed by LoopAgent (optimization). | Agent Architecture: "SequentialAgent orchestrates" | ADK SequentialAgent |

---

## 1.2 Non-Functional Requirements

| NFR_ID | Category | Requirement / Constraint | Measurement / Proof Path |
|---|---|---|---|
| NFR-PERF-001 | Performance | The full pipeline (parallel ingestion + iterative matching) shall complete in under 120 seconds for a single-state disaster scenario with up to 100 communities and 500 resources. | End-to-end timing from pipeline start to match list output. Measured during demo. |
| NFR-PERF-002 | Performance | Dashboard page load shall complete in under 3 seconds on a standard broadband connection. | Browser DevTools network timing. |
| NFR-PERF-003 | Performance | External API calls (FEMA, NOAA) shall each complete in under 10 seconds or fall back to cached data. | Per-call timing with timeout enforcement. |
| NFR-SEC-001 | Security | No personally identifiable information (PII) shall be stored or processed. All data is aggregated at census-tract level or higher. | Code review; data model audit. |
| NFR-SEC-002 | Security | API keys and secrets shall not be embedded in source code or client-side assets. | Secrets stored in environment variables or Google Secret Manager. |
| NFR-USA-001 | Usability | The operator dashboard shall be operable without training: Accept/Modify/Skip actions shall be self-evident from the interface. | Usability walkthrough during demo. |
| NFR-USA-002 | Usability | The dashboard shall use color and text together (not color alone) to convey vulnerability levels and match priority, ensuring accessibility for color-vision-deficient users. | Visual inspection; WCAG 2.1 AA contrast check. |
| NFR-OPS-001 | Operability | The system shall log all agent execution steps, API call results, and match decisions with timestamps for post-demo debugging. | Log output review. |
| NFR-OPS-002 | Operability | The system shall be deployable from a single command or script to Google Cloud Run. | Deployment script test. |
| NFR-REL-001 | Reliability | If any external API (FEMA, NOAA, CDC SVI) is unavailable, the system shall continue operating with cached or sample data and display a staleness warning to the operator. | Simulated API failure test. |
| NFR-REL-002 | Reliability | If the MatchOptimizer fails to converge within max_iterations, the system shall return the best allocation found so far rather than failing silently. | LoopAgent max_iterations test. |
| NFR-COM-001 | Compatibility | The system shall consume FEMA OpenFEMA API v2 (OData), NOAA NWS API (GeoJSON), and CDC SVI 2022 CSV without requiring API keys for FEMA/NOAA. | Integration test against live APIs. |
| NFR-SCA-001 | Scalability | The system shall handle a single-state disaster scenario (1 state, up to 100 affected census tracts, up to 500 resources) for the hackathon demo. Multi-state or national-scale scenarios are out of scope. | Demo scenario execution. |

### Real-Time SLA Classification

**Soft Real-Time.** The system must produce matches "in minutes instead of weeks" but there is no hard deadline where a missed computation window causes physical harm. A 2-minute vs. 5-minute completion time is a quality difference, not a safety failure.

### Threshold Enforcement Types
- NFR-PERF-001 (120s pipeline): **Soft** -- if exceeded, the system still returns results; the demo is less impressive.
- NFR-PERF-003 (10s API timeout): **Hard** -- enforced by HTTP timeout; triggers fallback to cached data.
- NFR-REL-002 (max_iterations): **Hard** -- enforced by LoopAgent configuration; returns best-so-far.

### SLA / Error Budget
- N/A -- Startup/Greenfield profile, hackathon scope. No production SLA. Target is 100% availability during the 4-minute demo window on March 29, 2026.

---

### 1.2.1 Sponsor / Reality Check (Hackathon Overlay)

**Google Cloud ADK Challenge (Primary Track):**
- Judging criteria: 30% Architecture, 30% Usefulness, 20% Technical, 20% Presentation.
- Architecture requirement: Must use Google ADK with ParallelAgent, LoopAgent, and A2A. Verified: `google-adk` pip package supports Agent, SequentialAgent, ParallelAgent, LoopAgent. A2A communication is supported.
- Model: gemini-2.5-flash (available, fast, cost-effective).
- Deployment: Must deploy on Google Cloud. Cloud Run is suitable for a containerized Python application.

**Climate Teach-In (Secondary Track):**
- Focus: Tampa Bay water resilience, equity, feasibility.
- Verified: FEMA API returns Florida disaster declarations (state='FL'). NOAA API returns Florida alerts (area=FL). CDC SVI data covers Florida census tracts.

**Oracle (Tertiary Track):**
- Focus: Human-centered AI.
- Addressed by: Human-in-the-loop design (Accept/Modify/Skip), accessibility in dashboard (NFR-USA-002).

**API Verification (conducted 2026-03-28):**
- FEMA OpenFEMA API: Working. `https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$filter=state eq 'FL'` returns results. No API key required.
- NOAA NWS API: Working. `https://api.weather.gov/alerts/active?area=FL` returns GeoJSON. User-Agent header recommended.
- CDC SVI: CSV available at `https://svi.cdc.gov/Documents/Data/2022/csv/states/SVI_2022_US.csv`. 158 columns, RPL_THEMES is overall vulnerability (0-1).
- Census Geocoder: Working. Address-to-FIPS-tract conversion available.

**Demo deadline:** March 29, 2026, 1:00 PM. All functionality must be demo-ready by then.

---

### 1.2.5 Capacity and Back-of-the-Envelope Estimation

**Current Scale Target: Tier 1 (0-10k DAU equivalent)**

This is a hackathon demo system. Expected concurrent users during demo: 1-3 (judges + presenter). Expected concurrent users if deployed for evaluation: up to 10.

| Dimension | Estimate | Basis |
|---|---|---|
| Concurrent users | 1-3 (demo), 10 (max evaluation) | Hackathon judging context |
| Pipeline executions/hour | 1-5 | Manual trigger by operator |
| FEMA API calls/pipeline | 1-2 | One query per disaster state |
| NOAA API calls/pipeline | 1-2 | One query per alert area |
| CDC SVI data size | ~50MB CSV (loaded once into pandas) | 158 columns x ~72,000 census tracts |
| Resources to match per run | Up to 500 | Single-state scenario |
| Communities to match per run | Up to 100 census tracts | Single-state disaster footprint |
| MatchOptimizer iterations | 5-20 per run | Convergence expected within 10 |
| Gemini API calls/pipeline | 10-30 (one per agent step per iteration) | 3 parallel agents + 5-20 optimizer iterations |
| Storage growth | Negligible (<1MB/run for match results) | In-memory during demo; no persistent storage required |
| Total pipeline latency budget | 120 seconds | NFR-PERF-001 |
| Breakdown: parallel ingestion | 30 seconds (bounded by slowest API) | FEMA/NOAA/SVI load |
| Breakdown: match optimization | 60-90 seconds (5-20 iterations x 3-5s each) | Gemini Flash inference + scoring |
| Bandwidth | <10MB/pipeline run | API responses + SVI CSV (cached after first load) |

**Next Scale Tier / Migration Horizon:**
- Tier 2 would require: persistent storage for match history, user authentication, multi-tenant agency isolation, and a proper queue for concurrent pipeline runs. First architectural boundary to change: in-memory state would need to move to a database.
- Not relevant for hackathon scope.

**Training / Fine-Tuning Memory Accounting:**
- N/A -- no training or fine-tuning. The system uses Gemini 2.5 Flash via API (hosted inference).

---

### Design Principle Tags (used in 1.3)

- P1 = Encapsulate what varies
- P2 = Program to interfaces, not implementations
- P3 = Favor composition over inheritance
- P4 = Single responsibility
- P5 = Strive for loose coupling
- P6 = Depend on abstractions (Dependency Inversion)
- P7 = Principle of least knowledge
- P8 = Fail-safe defaults / defensive design
- P9 = Open for extension, closed for modification
- P10 = Standardize when intuitive design is insufficient
- P11 = Prefer knowledge in the world over knowledge in the head
- P12 = Match architectural complexity to the current scale, risk, and evidence

---

## 1.3 Architecture Blueprint

### System Architecture Diagram

```
                            ReliefLink — System Architecture
 ========================================================================================

  EXTERNAL DATA SOURCES                    AGENT PIPELINE (Google ADK)
 ┌─────────────────────┐      ┌─────────────────────────────────────────────────────────┐
 │                     │      │                                                         │
 │  FEMA OpenFEMA API  │◄─────┤  ┌─────────────────────────────────────────────────┐    │
 │  (Disaster Decl.)   │      │  │           SequentialAgent (Orchestrator)         │    │
 │                     │      │  │                                                 │    │
 ├─────────────────────┤      │  │  ┌───────────────────────────────────────────┐  │    │
 │                     │      │  │  │         ParallelAgent (Data Gather)       │  │    │
 │  NOAA NWS API       │◄─────┤  │  │                                           │  │    │
 │  (Weather Alerts)   │      │  │  │  ┌─────────────┐  ┌──────────────────┐   │  │    │
 │                     │      │  │  │  │  Disaster    │  │   Resource       │   │  │    │
 ├─────────────────────┤      │  │  │  │  Monitor     │  │   Scanner        │   │  │    │
 │                     │      │  │  │  │  Agent       │  │   Agent          │   │  │    │
 │  CDC SVI Data       │◄─────┤  │  │  │ (FEMA+NOAA) │  │ (All channels)   │   │  │    │
 │  (Vulnerability)    │      │  │  │  └─────────────┘  └────────┬─────────┘   │  │    │
 │                     │      │  │  │                             │ A2A         │  │    │
 ├─────────────────────┤      │  │  │  ┌─────────────┐           │             │  │    │
 │                     │      │  │  │  │  Need        │◄──────────┘             │  │    │
 │  Census Geocoder    │◄─────┤  │  │  │  Mapper      │                        │  │    │
 │  (FIPS Lookup)      │      │  │  │  │  Agent       │                        │  │    │
 │                     │      │  │  │  │ (SVI+Needs)  │                        │  │    │
 └─────────────────────┘      │  │  │  └─────────────┘                        │  │    │
                              │  │  └───────────────────────────────────────────┘  │    │
                              │  │                      │                          │    │
                              │  │                      ▼                          │    │
                              │  │  ┌───────────────────────────────────────────┐  │    │
                              │  │  │      LoopAgent (Match Optimization)       │  │    │
                              │  │  │                                           │  │    │
                              │  │  │  ┌─────────────────────────────────────┐  │  │    │
                              │  │  │  │        MatchOptimizer Agent         │  │  │    │
                              │  │  │  │                                     │  │  │    │
                              │  │  │  │  Input: Resources + Needs + SVI     │  │  │    │
                              │  │  │  │  Process: Equity-weighted matching  │  │  │    │
                              │  │  │  │  Output: Prioritized routing plan   │  │  │    │
                              │  │  │  │  Loop: until converged or max=5     │  │  │    │
                              │  │  │  └─────────────────────────────────────┘  │  │    │
                              │  │  └───────────────────────────────────────────┘  │    │
                              │  └─────────────────────────────────────────────────┘    │
                              └─────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                              ┌─────────────────────────────────────────────────────────┐
                              │              Backend API Server (Flask)                  │
                              │  /api/run-pipeline    /api/matches    /api/decide        │
                              └─────────────────────────────────┬───────────────────────┘
                                                                │
                                                                ▼
                              ┌─────────────────────────────────────────────────────────┐
                              │               Web Dashboard (Frontend)                   │
                              │                                                         │
                              │  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐ │
                              │  │ Resources  │  │  Needs Map   │  │   Match List     │ │
                              │  │ Inventory  │  │  + SVI Heat  │  │   + Equity Score │ │
                              │  │ (Left)     │  │  (Center)    │  │   (Right)        │ │
                              │  └───────────┘  └──────────────┘  └──────────────────┘ │
                              │                                                         │
                              │           [ Accept ]  [ Modify ]  [ Skip ]              │
                              └─────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                               Agency Operator
                                          (Human-in-the-Loop)
```

### Data Flow Diagram

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │   FEMA   │     │   NOAA   │     │ CDC SVI  │
  │   API    │     │   API    │     │   CSV    │
  └────┬─────┘     └────┬─────┘     └────┬─────┘
       │                │                │
       ▼                ▼                ▼
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │ Disaster │     │ Resource │     │   Need   │
  │ Monitor  │     │ Scanner  │     │  Mapper  │
  └────┬─────┘     └────┬─────┘     └────┬─────┘
       │                │                │
       │         ┌──────┴────A2A────────┘
       │         │
       ▼         ▼
  ┌─────────────────────┐
  │   DisasterEvent     │
  │   Resource[]        │──────► ┌─────────────────────────┐
  │   Community[]       │        │    MatchOptimizer        │
  │   Need[]            │        │    (LoopAgent)           │
  └─────────────────────┘        │                         │
                                 │  Equity Score =          │
                                 │   (Need Severity × 0.5)  │
                                 │  + (SVI Score × 0.3)     │
                                 │  + (Proximity × 0.2)     │
                                 │                         │
                                 │  Loop until:             │
                                 │   delta < 0.05 or        │
                                 │   iterations = 5         │
                                 └────────┬────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────────────┐
                                 │   Match[]               │
                                 │   - resource_id         │
                                 │   - community_fips      │
                                 │   - equity_score        │
                                 │   - routing_plan        │
                                 │   - status: pending     │
                                 └────────┬────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────────────┐
                                 │   Operator Dashboard    │
                                 │                         │
                                 │  "500 cases water at    │
                                 │   Staging A → Zip 33610 │
                                 │   (SVI: 0.82)"          │
                                 │                         │
                                 │  [Accept] [Modify] [Skip]│
                                 └─────────────────────────┘
```

### Agent Execution Timeline

```
  Time ──────────────────────────────────────────────────────────────►

  Pipeline
  Trigger ──┐
            │
            ▼
  ┌─────────────────────────────────────────┐
  │         ParallelAgent                   │
  │                                         │
  │  DisasterMonitor ████████░░░░ (5-10s)  │
  │  ResourceScanner ██████████░░ (5-15s)  │
  │  NeedMapper      ████████████ (5-15s)  │
  │                       ▲                 │
  │                  A2A  │                 │
  │  ResourceScanner ◄────┘                │
  └─────────────────────────────────────────┘
            │
            ▼
  ┌─────────────────────────────────────────┐
  │         LoopAgent (max 5 iterations)    │
  │                                         │
  │  Iter 1: MatchOptimizer ████░ (2-5s)   │
  │  Iter 2: MatchOptimizer ███░░ (2-5s)   │
  │  Iter 3: MatchOptimizer ██░░░ (converge)│
  │           exit_loop() called            │
  └─────────────────────────────────────────┘
            │
            ▼
  ┌─────────────────────────────────────────┐
  │  Dashboard updated with matches         │
  │  Operator reviews (human time)          │
  │  Accept/Modify/Skip per match           │
  └─────────────────────────────────────────┘

  Total agent pipeline: ~30-60 seconds
  Total with operator: minutes (human-dependent)
```

---

### 1.3.A Critical Flow Inventory

| CF_ID | Flow Name | Trigger / Start State | End State | Topology | Direction | Notes |
|---|---|---|---|---|---|---|
| CF-01 | Disaster Detection & Ingestion | Operator triggers pipeline or scheduled poll | DisasterEvent created with footprint, severity, population | 1:N (1 trigger, N API calls) | Inbound | DisasterMonitor agent |
| CF-02 | Resource Inventory Aggregation | Pipeline trigger (parallel with CF-01, CF-03) | Resource list catalogued with location, quantity, owner, type | 1:N (1 trigger, N source queries) | Inbound | ResourceScanner agent |
| CF-03 | Community Need Assessment | Pipeline trigger (parallel with CF-01, CF-02) | Community list with vulnerability scores and quantified needs | 1:N (1 trigger, N tract lookups) | Inbound | NeedMapper agent |
| CF-04 | A2A Resource-Need Coordination | CF-02 and CF-03 outputs available | Coordinated resource-need cross-reference | 1:1 (ResourceScanner to NeedMapper) | Bidirectional | A2A message exchange |
| CF-05 | Iterative Match Optimization | ParallelAgent completes (CF-01/02/03/04) | Converged or max-iteration match list with equity scores and routing | Batch (iterative loop) | Internal | MatchOptimizer via LoopAgent |
| CF-06 | Operator Match Review | Match list presented on dashboard | Operator has Accepted, Modified, or Skipped each match | 1:1 (per operator per match) | Bidirectional | Human-in-the-loop |
| CF-07 | Post-Acceptance Re-Optimization | Operator accepts/skips a match | Updated match list with remaining resources re-optimized | 1:1 (acceptance triggers re-run) | Internal | MatchOptimizer re-run |

- **FR IDs covered:** FR-001 through FR-015 (all FRs map to at least one critical flow)
- **NFR IDs covered:** NFR-PERF-001 (pipeline timing), NFR-PERF-003 (API call timing), NFR-REL-001 (API fallback), NFR-REL-002 (convergence fallback)
- **Mapping note:** Each critical flow maps directly to the agent pipeline stages defined in the premise. CF-01/02/03 run in parallel (ParallelAgent). CF-05 runs as LoopAgent. CF-06/07 are the human-in-the-loop boundary.
- **Design principles applied:** P4, P5, P12
- **Principle rationale:** Each flow has a single responsibility (P4), flows are loosely coupled through well-defined data handoffs (P5), and the flow count matches actual system complexity without artificial decomposition (P12).
- **Pattern(s) used:** `NONE`
- **Pattern rationale:** Flow inventory is a structural enumeration, not a behavioral pattern application point.

---

### 1.3.B Components

#### B1. Orchestration Layer (SequentialAgent)
- **Responsibility:** Coordinates the full pipeline execution order. Owns the sequence: ParallelAgent (ingestion) then LoopAgent (optimization). Passes data between stages.
- **Must not do:** Must not perform data ingestion, scoring, or matching itself. Must not make resource allocation decisions.
- **Stateless/stateful:** Stateful for the duration of one pipeline run (holds pipeline context). No persistent state across runs.
- **Agent operating layer declaration:**
  - Tool-access boundary: Orchestration agent has no direct tool access; it delegates to sub-agents.
  - Working memory boundary: Pipeline run context (current DisasterEvent, Resource list, Community list, Match list).
  - Scheduling boundary: Google ADK SequentialAgent manages stage ordering; ParallelAgent manages concurrent sub-agent execution.
  - Policy/guardrail boundary: Max pipeline execution time (120s); max LoopAgent iterations.

#### B2. DisasterMonitor Agent
- **Responsibility:** Ingests disaster data from FEMA OpenFEMA API and NOAA NWS API. Produces a DisasterEvent object with geographic footprint, severity classification, and affected population estimate.
- **Must not do:** Must not assess community needs, score vulnerability, or allocate resources.
- **Stateless/stateful:** Stateless. Each invocation queries APIs fresh (with fallback to cache).
- **Tools:** FEMA API client, NOAA API client.

#### B3. ResourceScanner Agent
- **Responsibility:** Aggregates resource inventories from multiple source categories. Produces a list of Resource objects with location, quantity, type, and owning agency. Participates in A2A communication with NeedMapper.
- **Must not do:** Must not assess needs or compute equity scores. Must not make allocation decisions.
- **Stateless/stateful:** Stateless per invocation.
- **Tools:** Resource inventory query tools (API clients or structured data loaders for demo data representing federal/state/NGO/volunteer inventories).

#### B4. NeedMapper Agent
- **Responsibility:** Cross-references disaster footprint with CDC SVI data to identify affected communities, compute vulnerability scores, and quantify specific needs. Participates in A2A communication with ResourceScanner.
- **Must not do:** Must not ingest raw disaster data (that is DisasterMonitor's job). Must not perform resource matching.
- **Stateless/stateful:** Stateless per invocation. CDC SVI CSV is loaded into pandas as a read-only reference dataset.
- **Tools:** CDC SVI data loader, Census geocoder client, vulnerability scoring function.

#### B5. MatchOptimizer Agent (LoopAgent)
- **Responsibility:** Takes the Resource list and Community/Need list (with equity scores) and iteratively produces optimal resource-to-need matches. Each iteration refines the allocation. Terminates when allocation quality converges (delta < threshold) or max_iterations is reached.
- **Must not do:** Must not ingest data from external APIs. Must not present results to users. Must not execute dispatches.
- **Stateless/stateful:** Stateful within a LoopAgent run (tracks current best allocation and convergence delta). Stateless across pipeline runs.
- **Tools:** Matching/scoring function, equity score calculator.

#### B6. Web Dashboard (Frontend)
- **Responsibility:** Presents match recommendations to agency operators. Captures Accept/Modify/Skip decisions. Displays resource inventory, needs map with vulnerability heat overlay, and match list with equity scores.
- **Must not do:** Must not run agent logic. Must not directly call external APIs (all data comes through the backend). Must not auto-dispatch resources without operator approval.
- **Stateless/stateful:** Stateful for the user session (current view state, pending decisions). No server-side session persistence required.

#### B7. Backend API Server
- **Responsibility:** Serves the web dashboard. Exposes endpoints to trigger pipeline runs, retrieve current match lists, and submit operator decisions (Accept/Modify/Skip). Bridges between the agent pipeline and the frontend.
- **Must not do:** Must not contain agent orchestration logic (that belongs to the ADK orchestration layer). Must not directly query external APIs outside the agent pipeline.
- **Stateless/stateful:** Stateful for current pipeline run results (in-memory). No persistent database at hackathon scope.

#### B8. External API Integration Boundary
- **Responsibility:** Encapsulates all external API communication (FEMA, NOAA, CDC SVI, Census Geocoder). Provides consistent error handling, timeout enforcement, caching, and request pacing.
- **Must not do:** Must not interpret or score the data. Must not make allocation decisions.
- **External politeness:** Request pacing enforced: max 1 request/second per API host. Timeout: 10 seconds per call. User-Agent header set for NOAA API.

**Component-level traceability:**

- **FR IDs covered:** FR-001 (B2), FR-002 (B2), FR-003 (B3), FR-004 (B4), FR-005 (B4), FR-006 (B4/B5), FR-007 (B5), FR-008 (B5), FR-009 (B6), FR-010 (B6/B7), FR-011 (B5/B7), FR-012 (B1), FR-013 (B1/B5), FR-014 (B3/B4), FR-015 (B1)
- **NFR IDs covered:** NFR-PERF-001 (B1 pipeline timeout), NFR-PERF-002 (B6/B7), NFR-PERF-003 (B8), NFR-SEC-001 (all -- no PII in any component), NFR-SEC-002 (B8), NFR-USA-001 (B6), NFR-USA-002 (B6), NFR-OPS-001 (all -- logging), NFR-OPS-002 (B7 deployment), NFR-REL-001 (B8 fallback), NFR-REL-002 (B5 convergence), NFR-COM-001 (B8), NFR-SCA-001 (B1/B5 scale bounds)
- **Mapping note:** Each component owns a clearly bounded responsibility aligned with one or more FRs. Agent components (B2-B5) map to the Google ADK agent architecture. B6/B7 form the human-in-the-loop boundary. B8 isolates external system dependencies.
- **Design principles applied:** P1, P3, P4, P5, P7, P12
- **Principle rationale:** Each agent encapsulates a specific type of variation (P1: data source format, scoring algorithm, matching strategy). Agents are composed via ADK orchestration rather than inherited from a base class (P3). Each component has a single responsibility (P4). Components communicate through data handoffs, not shared internal state (P5). The dashboard only knows about match results, not agent internals (P7). Component count matches actual system complexity (P12).
- **Pattern(s) used:** Facade, Strategy
- **Pattern rationale:** B8 (External API Integration) acts as a Facade over heterogeneous external APIs. B5 (MatchOptimizer) uses a Strategy-like approach where the matching/scoring algorithm can be varied independently of the iteration loop.

---

### 1.3.C Responsibilities and Boundaries

| Component | Owns | Must Not Do | Coupling |
|---|---|---|---|
| B1 Orchestration (SequentialAgent) | Pipeline execution order, stage transitions, timeout enforcement | Data ingestion, scoring, matching, user interaction | Static: ADK runtime. Dynamic: invokes B2/B3/B4 (parallel), then B5 (loop). |
| B2 DisasterMonitor | Disaster detection, FEMA/NOAA data parsing, DisasterEvent creation | Need assessment, resource tracking, matching | Static: ADK Agent + B8 API clients. Dynamic: called by B1. |
| B3 ResourceScanner | Resource inventory aggregation, Resource object creation, A2A with B4 | Need assessment, equity scoring, dispatch | Static: ADK Agent + B8 API clients. Dynamic: called by B1, A2A with B4. |
| B4 NeedMapper | Community identification, SVI scoring, need quantification, A2A with B3 | Disaster detection, resource tracking, matching | Static: ADK Agent + B8 API clients + pandas/SVI data. Dynamic: called by B1, A2A with B3. |
| B5 MatchOptimizer | Resource-to-need matching, equity-weighted scoring, convergence logic | Data ingestion, API calls, user interaction | Static: ADK LoopAgent. Dynamic: receives data from B1 (via B2/B3/B4 outputs). |
| B6 Dashboard | UI rendering, operator interaction, visual presentation | Agent logic, API calls, auto-dispatch | Static: web framework (Streamlit or Flask). Dynamic: calls B7 API. |
| B7 Backend API | HTTP endpoints, pipeline triggering, operator decision capture | Agent orchestration internals, direct external API calls | Static: Flask/FastAPI + ADK. Dynamic: triggers B1, serves B6. |
| B8 External APIs | API communication, timeout, caching, pacing, error normalization | Data interpretation, scoring, decisions | Static: requests/httpx library. Dynamic: called by B2/B3/B4. |

**Handoff points:**
1. B1 → B2/B3/B4: Pipeline trigger passes disaster context (state, event type).
2. B2/B3/B4 → B1: Each agent returns its structured output (DisasterEvent, Resource list, Community/Need list).
3. B3 ↔ B4: A2A exchange for resource-need cross-referencing.
4. B1 → B5: Aggregated data from parallel stage passed to MatchOptimizer.
5. B5 → B7: Match results stored in backend memory.
6. B7 → B6: Match results served via API to dashboard.
7. B6 → B7: Operator decisions (Accept/Modify/Skip) submitted via API.
8. B7 → B5: Re-optimization triggered after operator decisions.

**Split-authority handling:** Each agency's operator can only Accept/Modify/Skip matches involving their agency's resources. The system does not enforce cross-agency authority; it defers to each operator's own agency scope.

- **FR IDs covered:** FR-010 (operator authority), FR-012/13/14/15 (agent orchestration boundaries)
- **NFR IDs covered:** NFR-OPS-001 (clear boundaries enable logging), NFR-SEC-001 (no PII crosses any boundary)
- **Mapping note:** Boundaries enforce that no component exceeds its authority. The human-in-the-loop boundary (B6/B7) is the critical trust gate.
- **Design principles applied:** P4, P5, P7
- **Principle rationale:** Single responsibility per component (P4). Components communicate only through defined handoff data, not shared mutable state (P5). Each component knows only about its immediate collaborators (P7).
- **Pattern(s) used:** `NONE`
- **Pattern rationale:** Boundaries are enforced by ADK agent isolation and API contract separation, not by a formal design pattern.

---

### 1.3.D Data Flow

#### Core Entities

**DisasterEvent**
| Attribute | Type | Description |
|---|---|---|
| disaster_id | String (FEMA declaration number) | PK. Source: FEMA API. |
| disaster_type | Enum (hurricane, flood, tornado, wildfire, ...) | From FEMA declaration type. |
| state | String (2-letter abbreviation) | Affected state. |
| declared_date | ISO 8601 datetime | Declaration date. |
| geographic_footprint | List of FIPS county codes | Affected counties from FEMA designation. |
| severity | Float (0-10) | Computed from declaration type + NOAA alert severity. |
| affected_population | Integer | Estimated from census data for affected counties. |
| active_alerts | List of NOAA Alert objects | Current weather alerts in affected area. |

**Resource**
| Attribute | Type | Description |
|---|---|---|
| resource_id | UUID (generated) | PK. Generated at inventory time. |
| type | Enum (supplies, personnel, shelter, funds, equipment) | Resource category. |
| subtype | String | Specific resource (e.g., "water_pallets", "medical_team"). |
| quantity | Integer | Available units. |
| location | Object {lat, lon, address, fips_code} | Current location. |
| owner_agency_id | String | FK to Agency. Who controls this resource. |
| status | Enum (available, allocated, in_transit, delivered) | Current allocation status. |

**Community**
| Attribute | Type | Description |
|---|---|---|
| fips_tract | String (11-digit FIPS tract code) | PK. From CDC SVI / Census. |
| county_fips | String (5-digit FIPS county code) | Parent county. |
| state | String (2-letter) | State. |
| population | Integer | Tract population from SVI data. |
| vulnerability_index | Float (0-1) | RPL_THEMES from CDC SVI. 1 = most vulnerable. |
| svi_themes | Object {socioeconomic, household, minority, housing} | Individual SVI theme scores. |

**Agency**
| Attribute | Type | Description |
|---|---|---|
| agency_id | String | PK. Identifier (e.g., "FEMA", "FL_EMA", "RED_CROSS"). |
| name | String | Display name. |
| type | Enum (federal, state, ngo, volunteer) | Agency category. |
| jurisdiction | String | Geographic scope. |

**Need**
| Attribute | Type | Description |
|---|---|---|
| need_id | UUID (generated) | PK. |
| community_fips_tract | String | FK to Community. |
| need_type | Enum (shelter, supplies, medical, evacuation, equipment) | What is needed. |
| severity | Float (0-10) | How urgent. Computed from disaster impact + population. |
| quantity_needed | Integer | Units required. |
| quantity_fulfilled | Integer | Units matched so far. |

**Match**
| Attribute | Type | Description |
|---|---|---|
| match_id | UUID (generated) | PK. |
| resource_id | UUID | FK to Resource. |
| need_id | UUID | FK to Need. |
| equity_score | Float (0-100) | Combined vulnerability + severity priority. Higher = serve first. |
| routing_plan | Object {origin, destination, distance_km, eta_hours} | How to get the resource there. |
| status | Enum (recommended, accepted, modified, skipped, dispatched, delivered) | Match lifecycle state. |
| operator_notes | String (nullable) | Operator comments on modification. |

#### Relationships
- DisasterEvent 1:N Community (a disaster affects many communities)
- Community 1:N Need (a community can have multiple needs)
- Agency 1:N Resource (an agency owns many resources)
- Resource 1:1 Match (a resource is matched to at most one need at a time)
- Need 1:N Match (a need can be partially fulfilled by multiple resource matches)

#### Source-of-Truth Ownership
- DisasterEvent: B2 (DisasterMonitor) creates; B1 (Orchestration) holds in pipeline context.
- Resource: B3 (ResourceScanner) creates; B7 (Backend) holds current state for dashboard.
- Community: B4 (NeedMapper) creates from SVI data; B7 holds for dashboard.
- Need: B4 (NeedMapper) creates; B5 (MatchOptimizer) updates fulfillment.
- Match: B5 (MatchOptimizer) creates; B7 (Backend) updates status from operator decisions.
- Agency: Static configuration (loaded at startup).

#### ID Generation Strategy
- disaster_id: FEMA-assigned declaration number (externally generated, globally unique).
- resource_id, need_id, match_id: Python `uuid.uuid4()`. Globally unique, no coordination needed at hackathon scale (single process).
- fips_tract, county_fips: Census Bureau assigned (externally generated, globally unique).
- agency_id: Static, manually assigned string identifiers.

#### Data Sensitivity Classification
- All data is **public** or **aggregated public**. No PII. No classified data. No HIPAA/FERPA data. CDC SVI is published open data. FEMA declarations are public record. NOAA alerts are public.
- Trust boundary: external API responses are treated as untrusted input (validated before use). Operator decisions are trusted (authenticated in production; demo assumes trusted access).

#### Data Movement Path
1. External APIs → B8 (raw JSON/CSV) → B2/B3/B4 (parsed into entities) → B1 (aggregated in pipeline context) → B5 (consumed for matching) → B7 (stored in memory for serving) → B6 (rendered in dashboard).
2. Operator decisions: B6 (UI action) → B7 (API call) → B5 (re-optimization trigger) → B7 (updated matches) → B6 (refreshed view).

- **FR IDs covered:** FR-001 (DisasterEvent), FR-003 (Resource), FR-004/FR-005 (Community, Need), FR-006/FR-007 (Match, equity_score), FR-010/FR-011 (Match.status lifecycle)
- **NFR IDs covered:** NFR-SEC-001 (no PII in any entity), NFR-COM-001 (data shapes match external API contracts), NFR-SCA-001 (entity counts bounded to single-state scenario)
- **Mapping note:** Every FR that produces or consumes data maps to a defined entity with explicit attributes and ownership. The data model directly implements the Nouns from the domain model.
- **Design principles applied:** P1, P4, P8
- **Principle rationale:** Each entity encapsulates the variation specific to its domain concept (P1). Each entity has a single owner (P4). Default values are safe: Match.status starts as "recommended", Resource.status starts as "available" (P8).
- **Pattern(s) used:** `NONE`
- **Pattern rationale:** Data entities are simple Python dataclasses/dicts at hackathon scale. No ORM, no repository pattern -- unnecessary complexity for in-memory storage.

---

### 1.3.E Communication and Contracts

#### CF-01: Disaster Detection & Ingestion

- **Flow ID:** CF-01
- **Endpoint/Trigger:** DisasterMonitor agent invoked by ParallelAgent (internal ADK call)
- **Transport:** In-process ADK agent invocation (no network hop between orchestrator and agent)
- **External calls:**
  - FEMA: `GET https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$filter=state eq '{state}'&$orderby=declarationDate desc&$top=10`
  - NOAA: `GET https://api.weather.gov/alerts/active?area={state}` (Header: `User-Agent: ReliefLink/1.0`)
- **Input contract:** `{ "state": "FL", "disaster_type": "hurricane" | null }`
- **Success output:** `{ "disaster_event": DisasterEvent }`
- **Error output:** `{ "error": "FEMA_API_UNAVAILABLE" | "NOAA_API_UNAVAILABLE", "fallback_used": true, "staleness_warning": "Using cached data from {timestamp}" }`
- **Timeout:** 10s per external API call (NFR-PERF-003). Total CF-01: 15s budget.

#### CF-02: Resource Inventory Aggregation

- **Flow ID:** CF-02
- **Endpoint/Trigger:** ResourceScanner agent invoked by ParallelAgent
- **Transport:** In-process ADK agent invocation
- **Input contract:** `{ "state": "FL", "disaster_footprint": [list of FIPS county codes] }`
- **Success output:** `{ "resources": [Resource, ...], "source_count": int, "sources": ["federal", "state", "ngo", ...] }`
- **Error output:** `{ "error": "RESOURCE_SCAN_PARTIAL", "resources": [...], "missing_sources": ["volunteer"] }`
- **Note:** For hackathon demo, resource inventory sources include structured demo data representing real inventory categories. At least 3 source categories must be represented (FR-003).

#### CF-03: Community Need Assessment

- **Flow ID:** CF-03
- **Endpoint/Trigger:** NeedMapper agent invoked by ParallelAgent
- **Transport:** In-process ADK agent invocation
- **External calls:**
  - CDC SVI CSV loaded into pandas (cached after first load)
  - Census Geocoder (optional, for address-to-tract resolution)
- **Input contract:** `{ "disaster_footprint": [FIPS county codes], "disaster_severity": float }`
- **Success output:** `{ "communities": [Community, ...], "needs": [Need, ...] }`
- **Error output:** `{ "error": "SVI_DATA_UNAVAILABLE", "fallback_used": true }`

#### CF-04: A2A Resource-Need Coordination

- **Flow ID:** CF-04
- **Endpoint/Trigger:** Initiated by ResourceScanner and NeedMapper during parallel execution
- **Transport:** Google ADK A2A protocol (in-process agent-to-agent messaging)
- **Communication dimension:** Asynchronous
- **Consistency dimension:** Eventual
- **Coordination dimension:** Choreographed
- **Contract:** ResourceScanner sends `{ "resources_summary": { "by_type": {...}, "by_location": {...} } }` to NeedMapper. NeedMapper sends `{ "needs_summary": { "by_type": {...}, "by_severity": {...} } }` to ResourceScanner. This allows each agent to refine its output based on the other's findings.
- **Trade-off rationale:** Asynchronous + eventual + choreographed is acceptable here because the A2A exchange is advisory (refining estimates), not transactional. No rollback complexity exists.

#### CF-05: Iterative Match Optimization

- **Flow ID:** CF-05
- **Endpoint/Trigger:** LoopAgent invoked by SequentialAgent after ParallelAgent completes
- **Transport:** In-process ADK LoopAgent iteration
- **Input contract:** `{ "resources": [Resource, ...], "needs": [Need, ...], "communities": [Community, ...], "max_iterations": 20, "convergence_threshold": 0.01 }`
- **Success output:** `{ "matches": [Match, ...], "iterations_run": int, "converged": bool, "total_equity_score": float }`
- **Error output:** `{ "error": "MAX_ITERATIONS_REACHED", "matches": [...], "converged": false }` (this is a graceful degradation, not a failure -- NFR-REL-002)

#### CF-06: Operator Match Review (Dashboard API)

- **Flow ID:** CF-06
- **Endpoint/Trigger:** `GET /api/matches` (dashboard loads match list), `POST /api/matches/{match_id}/decision` (operator submits decision)
- **Transport:** HTTP/JSON over HTTPS
- **Caller identity:** N/A for hackathon demo (no authentication). Production would require agency-scoped auth.
- **Input contract (GET):** Query params: `?status=recommended&sort=equity_score_desc`
- **Success output (GET):** `{ "matches": [Match, ...], "disaster_event": DisasterEvent, "summary": { "total_resources": int, "total_needs": int, "matched": int, "pending": int } }`
- **Input contract (POST):** `{ "decision": "accept" | "modify" | "skip", "notes": string | null, "modifications": { ... } | null }`
- **Success output (POST):** `{ "match_id": string, "new_status": string, "reoptimization_triggered": bool }`
- **Error output:** `{ "error": "MATCH_NOT_FOUND" | "INVALID_DECISION", "message": string }`
- **Rate/control:** N/A at hackathon scale. No rate limiting needed for 1-3 concurrent users.
- **Client-side resilience:** Dashboard retries failed GET requests once with 2s delay. POST requests are not auto-retried (operator re-submits manually).

#### CF-07: Post-Acceptance Re-Optimization

- **Flow ID:** CF-07
- **Endpoint/Trigger:** Triggered internally when operator accepts or skips a match (CF-06 POST)
- **Transport:** In-process call from B7 to B5
- **Input contract:** `{ "current_matches": [Match, ...], "accepted_matches": [match_ids], "skipped_matches": [match_ids], "remaining_resources": [Resource, ...], "remaining_needs": [Need, ...] }`
- **Success output:** `{ "updated_matches": [Match, ...], "iterations_run": int }`

- **FR IDs covered:** FR-001/FR-002 (CF-01), FR-003 (CF-02), FR-004/FR-005/FR-006 (CF-03), FR-014 (CF-04), FR-007/FR-008 (CF-05), FR-009/FR-010 (CF-06), FR-011 (CF-07)
- **NFR IDs covered:** NFR-PERF-001 (latency budgets per flow), NFR-PERF-003 (API timeouts), NFR-REL-001 (fallback contracts), NFR-REL-002 (convergence fallback), NFR-COM-001 (external API contract compatibility)
- **Mapping note:** Every FR has a corresponding critical flow with a defined contract. Error contracts enforce fail-safe behavior (NFR-REL-001/002).
- **Design principles applied:** P2, P5, P8, P10
- **Principle rationale:** Contracts define interfaces, not implementations (P2). Each flow can change its internals without affecting callers (P5). Error outputs include fallback data and staleness warnings rather than bare failures (P8). JSON contracts standardize communication where multiple formats could cause confusion (P10).
- **Pattern(s) used:** Adapter
- **Pattern rationale:** B8 (External API Integration) adapts heterogeneous external API responses (OData, GeoJSON, CSV) into the uniform internal contract shapes consumed by agents.

---

### 1.3.F Failure Modes

#### FM-01: FEMA API Unavailable

- **Failure ID:** FM-01
- **Trigger:** FEMA OpenFEMA API returns HTTP error or times out (>10s).
- **Detection:** HTTP timeout or non-2xx status code (passive). No active health check.
- **Fallback behavior:** Return cached last-known disaster declarations for the target state. If no cache exists, return a curated sample dataset representing a recent Florida hurricane scenario.
- **Recovery class:** Graceful Degradation
- **User-visible error:** Dashboard displays: "Disaster data is from [timestamp]. Live FEMA feed unavailable. Data may not reflect the latest declarations."
- **Observability:** Log `WARN: FEMA API timeout/error. Status={code}. Falling back to cached data from {timestamp}.`
- **Anti-cascading:** Timeout is per-call (10s). No retry storm -- single retry with 2s delay, then fallback.

#### FM-02: NOAA API Unavailable

- **Failure ID:** FM-02
- **Trigger:** NOAA NWS API returns HTTP error or times out (>10s).
- **Detection:** HTTP timeout or non-2xx status code.
- **Fallback behavior:** DisasterEvent is created without active weather alerts. Severity scoring uses FEMA declaration data only.
- **Recovery class:** Graceful Degradation
- **User-visible error:** Dashboard displays: "Weather alert data unavailable. Showing disaster data without active alerts."
- **Observability:** Log `WARN: NOAA API timeout/error. Proceeding without active alerts.`

#### FM-03: CDC SVI Data Load Failure

- **Failure ID:** FM-03
- **Trigger:** CDC SVI CSV fails to download or parse.
- **Detection:** File load exception or pandas parse error.
- **Fallback behavior:** Use a pre-bundled subset of CDC SVI data for Florida census tracts (included in the deployment artifact). If bundled data also fails, assign a default vulnerability index of 0.5 to all communities and log a critical warning.
- **Recovery class:** Graceful Degradation
- **User-visible error:** "Vulnerability data is from bundled dataset. Live CDC data unavailable."
- **Observability:** Log `ERROR: CDC SVI CSV load failed. Using bundled fallback.`

#### FM-04: MatchOptimizer Non-Convergence

- **Failure ID:** FM-04
- **Trigger:** LoopAgent reaches max_iterations (20) without convergence_threshold being met.
- **Detection:** LoopAgent iteration counter reaches limit.
- **Fallback behavior:** Return the best allocation found in the final iteration. Flag all matches with `convergence_note: "Best-effort allocation. Optimization did not fully converge."` (NFR-REL-002).
- **Recovery class:** Graceful Degradation
- **User-visible error:** Dashboard displays: "Allocation is best-effort (optimization still improving when iteration limit reached). Review carefully."
- **Observability:** Log `WARN: MatchOptimizer reached max_iterations={n}. Final delta={d}. Returning best-effort allocation.`

#### FM-05: Gemini API Unavailable or Rate Limited

- **Failure ID:** FM-05
- **Trigger:** Gemini 2.5 Flash API returns 429 (rate limit) or 5xx error.
- **Detection:** HTTP status code from Gemini API response.
- **Fallback behavior:** Retry with exponential backoff (1s, 2s, 4s, max 3 retries). If all retries fail, the pipeline fails with a clear error message. No silent degradation is possible because agent reasoning requires the LLM.
- **Recovery class:** Retry then Fail Closed
- **User-visible error:** "AI service temporarily unavailable. Please retry in 30 seconds."
- **Observability:** Log `ERROR: Gemini API failed after {n} retries. Status={code}. Pipeline aborted.`
- **Anti-cascading:** Exponential backoff prevents retry storms. Circuit break after 3 failures.

#### FM-06: Pipeline Timeout (>120s)

- **Failure ID:** FM-06
- **Trigger:** Total pipeline execution exceeds 120 seconds.
- **Detection:** Pipeline-level timer in B1 (Orchestration).
- **Fallback behavior:** If ParallelAgent is still running, cancel remaining API calls and proceed with whatever data has been collected. If LoopAgent is running, stop iteration and return current best allocation.
- **Recovery class:** Graceful Degradation
- **User-visible error:** "Pipeline timed out. Showing partial results based on available data."
- **Observability:** Log `WARN: Pipeline timeout at {elapsed}s. Stage={current_stage}. Returning partial results.`

- **FR IDs covered:** FR-001/FR-002 (FM-01/02 API fallback), FR-004 (FM-03 SVI fallback), FR-007/FR-008 (FM-04 convergence fallback), FR-012/FR-013/FR-015 (FM-06 pipeline timeout)
- **NFR IDs covered:** NFR-PERF-001 (FM-06), NFR-PERF-003 (FM-01/02 timeout), NFR-REL-001 (FM-01/02/03), NFR-REL-002 (FM-04), NFR-OPS-001 (all FM observability)
- **Mapping note:** Every external dependency and convergence risk has a defined failure mode with graceful degradation. The system never fails silently (loud-failure rule). Every failure is logged and surfaced to the operator.
- **Design principles applied:** P8, P11
- **Principle rationale:** All failure modes default to safe, degraded behavior rather than crash or silent data loss (P8). Staleness warnings and convergence notes make system state visible in the world, not hidden in logs only (P11).
- **Pattern(s) used:** `NONE`
- **Pattern rationale:** Failure handling uses straightforward try/except with fallback values. No circuit breaker library or formal state pattern is needed at hackathon scale.

---

### 1.3.G Technology Stack

| Technology | Role | Why Chosen | NFR Fit |
|---|---|---|---|
| Python 3.11+ | Primary language | Google ADK is Python-native. Team proficiency. Fastest path to demo. | NFR-OPS-002 (simple deployment) |
| google-adk | Agent framework | Hard constraint. Provides Agent, SequentialAgent, ParallelAgent, LoopAgent, A2A. | FR-012/13/14/15 (agent architecture requirements) |
| gemini-2.5-flash | LLM model | Fast, cost-effective, sufficient for coordination reasoning. Google Cloud native. | NFR-PERF-001 (speed), NFR-SCA-001 (cost at demo scale) |
| pandas | SVI data processing | Standard for CSV/tabular data. CDC SVI is 158-column CSV with ~72K rows. | NFR-COM-001 (CSV compatibility) |
| requests / httpx | HTTP client | Standard Python HTTP library for FEMA/NOAA API calls. | NFR-PERF-003 (timeout support), NFR-COM-001 |
| Flask or Streamlit | Web framework (dashboard) | Flask: lightweight, familiar, full control. Streamlit: fastest to build data dashboards. Decision deferred to implementation. | NFR-PERF-002 (page load speed), NFR-USA-001 (usability) |
| Docker | Containerization | Required for Cloud Run deployment. Reproducible builds. | NFR-OPS-002 (single-command deploy) |
| Google Cloud Run | Compute platform | Hard constraint (Google Cloud). Serverless, scales to zero, no infra management. | NFR-OPS-002, NFR-SCA-001 |
| Google Secret Manager | Secret storage | Google Cloud native. Keeps API keys out of code. | NFR-SEC-002 |
| uuid (Python stdlib) | ID generation | uuid4 is sufficient for single-process, hackathon-scale ID generation. | Data Flow ID strategy |

**Build determinism:**
- `requirements.txt` with pinned versions (e.g., `google-adk==1.x.x`, `pandas==2.x.x`).
- Docker image built from pinned base image (`python:3.11-slim`).
- No floating version selectors.

**Storage/runtime fragmentation:**
- No specialized database, no vector store, no cache layer, no message broker. All state is in-memory during pipeline runs. This is justified by Tier 1 scale (1-3 concurrent users, no persistence needed).

- **FR IDs covered:** FR-012/13/14/15 (google-adk), FR-001/02 (requests for API calls), FR-004 (pandas for SVI), FR-009 (Flask/Streamlit for dashboard)
- **NFR IDs covered:** NFR-PERF-001/002/003 (performance-fit stack), NFR-SEC-002 (Secret Manager), NFR-OPS-002 (Docker + Cloud Run), NFR-COM-001 (standard HTTP/CSV libraries), NFR-SCA-001 (Cloud Run scaling)
- **Mapping note:** Every technology choice traces to a hard constraint, a functional requirement, or a non-functional requirement. No technology is included speculatively.
- **Design principles applied:** P5, P12
- **Principle rationale:** Minimal technology surface area matches actual scale and risk (P12). Standard, well-supported libraries reduce coupling to niche tools (P5).
- **Pattern(s) used:** `NONE`
- **Pattern rationale:** Technology selection is a decision, not a behavioral pattern. The stack is intentionally simple.

---

### 1.3.H Major Decision Records

#### MDR-01: Google ADK as Agent Framework

- **Decision:** Use Google ADK (google-adk) for all agent orchestration.
- **Why chosen:** Hard constraint from hackathon track (Google Cloud ADK Challenge). Also provides native support for SequentialAgent, ParallelAgent, LoopAgent, and A2A -- all required by the architecture.
- **Alternatives considered:** LangChain/LangGraph (no ParallelAgent/LoopAgent primitives), CrewAI (no Google Cloud ADK track eligibility), custom orchestration (too much scaffolding for hackathon timeline).
- **Key tradeoff:** Locked into Google ecosystem and Gemini models. Acceptable because the hackathon track requires it and Gemini 2.5 Flash is performant.
- **Assumptions:** google-adk pip package is stable enough for demo use. A2A protocol works for in-process agent communication.
- **Hypothesis:** Google ADK's built-in agent types (Parallel, Loop, Sequential) will reduce orchestration code by >50% compared to custom implementation.
- **Evidence that would invalidate:** ADK agent types have bugs that prevent reliable pipeline execution; A2A protocol does not support the message exchange pattern we need.
- **Principle basis:** P12 (match complexity to scale -- use framework rather than building from scratch)
- **Pattern basis:** `NONE`
- **ADR required?** No (externally mandated constraint, not an architectural choice)

#### MDR-02: In-Memory State (No Database)

- **Decision:** Store all pipeline state in-memory (Python dicts/dataclasses). No database.
- **Why chosen:** Hackathon scope. 1-3 concurrent users. No persistence requirement. Eliminates database setup, schema management, and deployment complexity.
- **Alternatives considered:** SQLite (simple but adds ORM/migration overhead), Firestore (Google Cloud native but adds latency and complexity), PostgreSQL (over-engineered for demo).
- **Key tradeoff:** No data survives process restart. No multi-instance scaling. Acceptable at hackathon scale.
- **Assumptions:** Demo runs are short-lived. No need to persist match history across sessions.
- **Hypothesis:** In-memory state will be sufficient for all demo scenarios and will save >4 hours of development time.
- **Evidence that would invalidate:** Judges require persistent match history or multi-user concurrent access.
- **Principle basis:** P12 (match complexity to current scale)
- **Pattern basis:** `NONE`
- **ADR required?** No (standard hackathon simplification)

#### MDR-03: Equity Score = Vulnerability Index x Need Severity

- **Decision:** Equity score is computed as `equity_score = vulnerability_index * need_severity_weight + need_severity * (1 - need_severity_weight)` where `need_severity_weight` defaults to 0.4 (vulnerability gets 60% weight).
- **Why chosen:** Vulnerability must dominate the ranking to fulfill the "equity-first" premise. Pure need-severity ranking would reproduce the status quo (wealthy areas with better reporting infrastructure would score highest). Pure vulnerability ranking ignores actual disaster impact.
- **Alternatives considered:** Equal weighting (50/50 -- does not sufficiently prioritize vulnerable communities), pure vulnerability ranking (ignores actual need), multi-criteria Pareto optimization (too complex for hackathon demo, harder to explain in 4 minutes).
- **Key tradeoff:** The 60/40 weighting is a policy choice, not a mathematical optimum. Different stakeholders may prefer different weights.
- **Assumptions:** CDC SVI RPL_THEMES is a reasonable proxy for community vulnerability in disaster contexts.
- **Hypothesis:** A 60/40 vulnerability-to-severity weighting will produce visibly different (and more equitable) allocations compared to severity-only ranking in the Tampa Bay demo scenario.
- **Evidence that would invalidate:** Domain experts (emergency managers) reject the weighting as unrealistic or counterproductive.
- **Principle basis:** P1 (encapsulate the weighting formula so it can be tuned), P9 (open for extension -- weight parameter is configurable)
- **Pattern basis:** Strategy (the scoring function can be swapped)
- **ADR required?** Yes
- **ADR title/location:** `docs/adr/ADR-001-equity-score-formula.md`

#### MDR-04: Streamlit vs Flask for Dashboard

- **Decision:** Deferred to implementation. Both are viable. Streamlit is faster to build; Flask gives more UI control.
- **Why chosen:** Decision deferred because both options meet all NFRs and the choice depends on implementation-time UX needs.
- **Alternatives considered:** React (too much setup time for hackathon), Gradio (less control over layout), plain HTML/JS (more work than Flask).
- **Key tradeoff:** Streamlit is faster to build but harder to customize. Flask is more work but gives pixel-level control for a polished demo.
- **Assumptions:** Either choice can be implemented in <4 hours.
- **Hypothesis:** The chosen framework will produce a demo-quality dashboard within the hackathon timeline.
- **Evidence that would invalidate:** The chosen framework cannot render a map/heat overlay with vulnerability data within the time budget.
- **Principle basis:** P12 (defer decisions until the last responsible moment when information is better)
- **Pattern basis:** `NONE`
- **ADR required?** No (reversible, low-stakes decision)

---

### 1.3.I Architecture Coverage Gate

#### FR Coverage Matrix

| FR_ID | Mapped (Y/N) | 1.3 Section Ref | Owning Component/Path |
|---|---|---|---|
| FR-001 | Y | 1.3.B (B2), 1.3.E (CF-01), 1.3.F (FM-01) | DisasterMonitor Agent via FEMA API |
| FR-002 | Y | 1.3.B (B2), 1.3.E (CF-01), 1.3.F (FM-02) | DisasterMonitor Agent via NOAA API |
| FR-003 | Y | 1.3.B (B3), 1.3.E (CF-02) | ResourceScanner Agent |
| FR-004 | Y | 1.3.B (B4), 1.3.E (CF-03), 1.3.F (FM-03) | NeedMapper Agent via CDC SVI |
| FR-005 | Y | 1.3.B (B4), 1.3.E (CF-03) | NeedMapper Agent |
| FR-006 | Y | 1.3.B (B4/B5), 1.3.D (Match entity), 1.3.H (MDR-03) | NeedMapper + MatchOptimizer |
| FR-007 | Y | 1.3.B (B5), 1.3.E (CF-05) | MatchOptimizer Agent (LoopAgent) |
| FR-008 | Y | 1.3.B (B5), 1.3.E (CF-05), 1.3.F (FM-04) | MatchOptimizer convergence logic |
| FR-009 | Y | 1.3.B (B6/B7), 1.3.E (CF-06) | Dashboard + Backend API |
| FR-010 | Y | 1.3.B (B6/B7), 1.3.C (handoff 7), 1.3.E (CF-06) | Dashboard Accept/Modify/Skip |
| FR-011 | Y | 1.3.B (B5/B7), 1.3.E (CF-07) | Backend triggers re-optimization |
| FR-012 | Y | 1.3.B (B1), 1.3.G (google-adk) | SequentialAgent → ParallelAgent |
| FR-013 | Y | 1.3.B (B1/B5), 1.3.G (google-adk) | LoopAgent for MatchOptimizer |
| FR-014 | Y | 1.3.B (B3/B4), 1.3.E (CF-04) | A2A between ResourceScanner and NeedMapper |
| FR-015 | Y | 1.3.B (B1), 1.3.A (flow sequence) | SequentialAgent orchestration |

#### NFR Coverage Matrix

| NFR_ID | Mapped (Y/N) | 1.3 Section Ref | Enforcing Layer/Mechanism |
|---|---|---|---|
| NFR-PERF-001 | Y | 1.3.A (latency budgets), 1.3.F (FM-06) | Pipeline timeout in Orchestration Layer (B1) |
| NFR-PERF-002 | Y | 1.3.B (B6/B7), 1.3.G (Flask/Streamlit) | Lightweight frontend framework |
| NFR-PERF-003 | Y | 1.3.B (B8), 1.3.E (CF-01/02/03), 1.3.F (FM-01/02) | HTTP timeout enforcement in API Integration |
| NFR-SEC-001 | Y | 1.3.D (data sensitivity classification) | All entities use aggregated public data only |
| NFR-SEC-002 | Y | 1.3.G (Google Secret Manager) | Secrets in env vars / Secret Manager, not in code |
| NFR-USA-001 | Y | 1.3.B (B6) | Dashboard self-evident UI (Accept/Modify/Skip) |
| NFR-USA-002 | Y | 1.3.B (B6) | Color + text for vulnerability levels |
| NFR-OPS-001 | Y | 1.3.F (all FM observability) | Structured logging in every component |
| NFR-OPS-002 | Y | 1.3.G (Docker + Cloud Run) | Single-command deployment |
| NFR-REL-001 | Y | 1.3.F (FM-01/02/03) | Cached/bundled fallback data |
| NFR-REL-002 | Y | 1.3.F (FM-04) | LoopAgent max_iterations with best-so-far return |
| NFR-COM-001 | Y | 1.3.E (CF-01/02/03 external call contracts) | Standard HTTP client with format-specific parsers |
| NFR-SCA-001 | Y | 1.3.B (B1/B5 scale bounds), 1.3.G (Cloud Run) | Bounded input sizes, single-instance deployment |

#### Principle Tagging Check

| 1.3 Subsection | Design Principles Applied | Principle Rationale Present |
|---|---|---|
| 1.3.A Critical Flow Inventory | P4, P5, P12 | Yes |
| 1.3.B Components | P1, P3, P4, P5, P7, P12 | Yes |
| 1.3.C Responsibilities and Boundaries | P4, P5, P7 | Yes |
| 1.3.D Data Flow | P1, P4, P8 | Yes |
| 1.3.E Communication and Contracts | P2, P5, P8, P10 | Yes |
| 1.3.F Failure Modes | P8, P11 | Yes |
| 1.3.G Technology Stack | P5, P12 | Yes |

**Completion verdict:** All FR IDs mapped. All NFR IDs mapped. All 1.3 subsections include principle tags and rationale. Architecture Coverage Gate: **PASS.**

---

## 2.0 Infrastructure Premise

The infrastructure must support a single-process Python application (agent pipeline + web dashboard) deployed to Google Cloud, accessible via public HTTPS for demo purposes, with outbound access to FEMA, NOAA, CDC, and Gemini APIs.

This is a hackathon deployment. High availability, multi-region, disaster recovery, and production-grade security are not required. The infrastructure must be simple, fast to provision, and cost-effective (ideally free-tier or minimal-cost).

The infrastructure design satisfies the following system NFRs:
- NFR-OPS-002: Single-command deployment to Cloud Run.
- NFR-PERF-002: Dashboard page load <3s (Cloud Run provides HTTPS with low-latency global edge).
- NFR-SEC-002: Secrets in Google Secret Manager, not in code.
- NFR-SCA-001: Cloud Run handles the single-instance, low-traffic demo workload.

---

## 2.1 Hosting Requirements

| HostReq_ID | Component | Required Capability / Service | Condition / Purpose | Trace Source |
|---|---|---|---|---|
| HR-001 | Agent Pipeline + Backend API (B1-B5, B7, B8) | Containerized compute with outbound internet access, min 1 vCPU, 1GB RAM | Run Python application with pandas (SVI CSV ~50MB in memory), google-adk, and Gemini API calls | NFR-OPS-002, NFR-PERF-001 |
| HR-002 | Web Dashboard (B6) | Served from same container as B7 (co-located) or as static assets behind the same endpoint | Minimize deployment complexity; single URL for judges | NFR-PERF-002, NFR-USA-001 |
| HR-003 | Secret Storage | Managed secret store for Gemini API key and any other credentials | Keep secrets out of source code and container images | NFR-SEC-002 |
| HR-004 | Container Registry | Private container image storage with pull access from compute service | Store and deploy Docker images | NFR-OPS-002 |
| HR-005 | HTTPS Ingress | Public HTTPS endpoint with TLS termination | Judges access dashboard via browser without certificate warnings | NFR-PERF-002 |
| HR-006 | CDC SVI Data | Either bundled in container image or fetched at startup and cached in memory | NeedMapper requires SVI CSV data; bundling avoids runtime download dependency | NFR-REL-001 |

---

## 2.2 Environmental Constraints

| Constraint_ID | Category | Constraint / Limit | Source / Proof Path |
|---|---|---|---|
| IC-001 | Availability | Single-region, single-instance deployment is acceptable. No multi-AZ requirement. Target: 100% availability during 4-minute demo window. | Hackathon scope. No production SLA. |
| IC-002 | Security | No PII processed or stored. Gemini API key stored in Secret Manager. No other secrets required (FEMA/NOAA APIs are public). | NFR-SEC-001, NFR-SEC-002 |
| IC-003 | Security | Container runs as non-root user. No SSH access needed. | Standard Cloud Run security posture. |
| IC-004 | Networking | Container needs outbound HTTPS to: `www.fema.gov`, `api.weather.gov`, `svi.cdc.gov`, `geocoding.geo.census.gov`, `generativelanguage.googleapis.com` (Gemini). Inbound: HTTPS on port 8080 (Cloud Run default). | FR-001/02/03/04, Gemini API access |
| IC-005 | Compliance | N/A -- Startup/Greenfield profile, hackathon scope. No HIPAA, FedRAMP, or data residency requirements. All data is public. | Ethical intake gate (1.0.0.1) |
| IC-006 | Cost | Target: $0-5 total spend for hackathon. Cloud Run free tier: 2M requests/month, 360K vCPU-seconds/month, 180K GiB-seconds/month. Demo usage is well within free tier. | Google Cloud free tier documentation |
| IC-007 | Cost | Gemini 2.5 Flash API: pricing per input/output token. Estimated demo cost: <$0.50 for 10-30 API calls per pipeline run x 5-10 demo runs. | Google AI pricing page |

### Provider/Platform Limit Check

- **Cloud Run:** Max container instance memory: 32 GiB (we need 1 GB). Max request timeout: 3600s (we need 120s). Max concurrent requests per instance: 1000 (we need 1-3). Cold start: 2-10s for Python containers. Mitigation: keep min-instances=1 to avoid cold start during demo.
- **Gemini 2.5 Flash:** Rate limit: 1000 RPM on free tier, 4000 RPM on paid. We need ~30 calls per pipeline run. Well within limits.
- **FEMA API:** No documented rate limit. Best practice: <1 req/s.
- **NOAA API:** Recommends User-Agent header. No documented rate limit.

---

## 2.3 Infrastructure Architecture Blueprint

### 2.3.A Infrastructure Services

| Service | Provider/Tool | Role |
|---|---|---|
| Compute | Google Cloud Run | Runs the containerized Python application (agent pipeline + backend API + dashboard) |
| Container Registry | Google Artifact Registry | Stores Docker images for Cloud Run deployment |
| Secret Management | Google Secret Manager | Stores Gemini API key |
| HTTPS Ingress | Cloud Run built-in (managed TLS) | Provides public HTTPS endpoint with auto-provisioned TLS certificate |
| DNS (optional) | Cloud Run auto-generated URL | `https://<service>-<hash>-uc.a.run.app`. Custom domain optional but not required for demo. |

**Services NOT used (justified by P12 -- match complexity to scale):**
- Persistent data service: N/A. All state is in-memory. No database.
- Cache/transient state service: N/A. CDC SVI CSV cached in application memory (pandas DataFrame).
- File/object storage: N/A. CDC SVI CSV bundled in Docker image or fetched at startup.
- Messaging/event transport: N/A. All agent communication is in-process via Google ADK.

### 2.3.B Responsibilities and Boundaries

**Cloud Run:**
- Owns: Container lifecycle, auto-scaling (min 1, max 1 for demo), HTTPS ingress, TLS termination.
- Must not do: Must not be configured with >1 max instance (avoids split-brain with in-memory state).
- Connection quota: N/A (single instance).

**Artifact Registry:**
- Owns: Docker image storage and versioning.
- Must not do: Must not store secrets or environment-specific configuration in images.

**Secret Manager:**
- Owns: Gemini API key storage, access control.
- Must not do: Must not be used for application configuration (only secrets).

**Data lifecycle:**
- N/A -- Startup/Greenfield profile, hackathon scope. No hot/warm/cold storage tiers. No data retention policy. All data is ephemeral (in-memory, lost on container restart).

### 2.3.C Network Traffic Flow

```
[Judge's Browser]
       |
       | HTTPS (port 443)
       v
[Cloud Run HTTPS Ingress / TLS Termination]
       |
       | HTTP (port 8080, internal)
       v
[Container: Python App]
       |
       |--- outbound HTTPS ---> www.fema.gov (FEMA API)
       |--- outbound HTTPS ---> api.weather.gov (NOAA API)
       |--- outbound HTTPS ---> svi.cdc.gov (CDC SVI CSV)
       |--- outbound HTTPS ---> geocoding.geo.census.gov (Census Geocoder)
       |--- outbound HTTPS ---> generativelanguage.googleapis.com (Gemini API)
```

**Trust zones:**
1. **Public internet:** Judge's browser to Cloud Run ingress. Protected by TLS (auto-provisioned by Cloud Run).
2. **Cloud Run internal:** Ingress to container. Private. No direct access from internet to container port.
3. **Outbound to external APIs:** Container to FEMA/NOAA/CDC/Census. Public HTTPS. No authentication needed (except Gemini API key in header).
4. **Outbound to Google APIs:** Container to Gemini API. Authenticated via API key from Secret Manager.

**Security groups / firewall:**
- Cloud Run default: inbound HTTPS only (port 443). No SSH, no other ports.
- Outbound: all HTTPS allowed (required for external API access). No VPC needed at hackathon scale.

### 2.3.D Configuration and Access Control

**IAM:**
- Cloud Run service account: `relieflink-sa@<project>.iam.gserviceaccount.com`
  - Roles: `roles/secretmanager.secretAccessor` (read Gemini API key), `roles/run.invoker` (allow public access to Cloud Run service).
- Deployment account (developer): `roles/run.admin`, `roles/artifactregistry.writer`, `roles/secretmanager.admin`.

**Secret management:**
- Gemini API key stored as Secret Manager secret: `projects/<project>/secrets/gemini-api-key/versions/latest`.
- Mounted as environment variable `GEMINI_API_KEY` in Cloud Run service configuration.
- Rotation: N/A for hackathon. API key can be revoked and re-created manually.

**Environment isolation:**
- Single environment (no staging/production split at hackathon scale).
- Cloud Run service name includes "hackathon" prefix to prevent confusion with any other project resources: `relieflink-hackathon`.

**Architectural forcing functions:**
- N/A -- Startup/Greenfield profile, hackathon scope. No interlocks, lockouts, or lock-ins beyond Cloud Run's built-in deployment controls.

### 2.3.E Infrastructure Failure Modes

| Failure ID | Trigger / Degraded Domain | Fallback / Degraded Behavior | Recovery Action | User/Operator Effect |
|---|---|---|---|---|
| IFM-01 | Cloud Run container crash | Cloud Run auto-restarts container (built-in). | Automatic restart (typically <10s). | Brief interruption. Dashboard reload required. |
| IFM-02 | Cloud Run cold start during demo | Set min-instances=1 to keep one warm instance. | Pre-warm by loading dashboard 5 minutes before demo. | First request may take 5-10s instead of <3s if cold. |
| IFM-03 | Gemini API outage | FM-05 (application-level retry + fail). | Wait and retry. No infrastructure-level mitigation. | Pipeline fails. Operator sees error message. |
| IFM-04 | Google Cloud regional outage | No multi-region failover at hackathon scale. | Switch to local development server (laptop) as emergency backup demo. | Demo continues on localhost if Cloud Run is down. |
| IFM-05 | Secret Manager unavailable | Container cannot read Gemini API key. | Fallback: set API key directly as Cloud Run environment variable (less secure, acceptable for demo). | Pipeline cannot call Gemini. Manual env var fix needed. |

### 2.3.F Infrastructure Technology Stack

| Tool | Role | Why |
|---|---|---|
| Docker | Containerization | Required for Cloud Run. Dockerfile defines reproducible build. |
| Google Cloud CLI (`gcloud`) | Deployment orchestration | Single-command deploy: `gcloud run deploy`. |
| Google Artifact Registry | Container image storage | Google Cloud native. Integrated with Cloud Run. |
| Google Secret Manager | Secret storage | Google Cloud native. IAM-integrated access control. |
| Makefile or shell script | Build/deploy automation | `make deploy` wraps Docker build + push + Cloud Run deploy for single-command deployment (NFR-OPS-002). |

**Declarative infrastructure:**
- Cloud Run service configuration is declarative (YAML or `gcloud run deploy` flags).
- No Terraform or Pulumi at hackathon scale -- the infrastructure is 4 resources (Cloud Run service, Artifact Registry repo, Secret Manager secret, IAM bindings) that can be provisioned in <10 minutes with `gcloud` commands.
- A `deploy.sh` script captures the exact commands for reproducibility.

---

*Document version: 1.0. Created: 2026-03-28. Hackathon: HackUSF 2026. Judging: 2026-03-29 1:00 PM.*
