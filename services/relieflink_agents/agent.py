"""
ADK Dev UI entry point for ReliefLink.


Uses an LlmAgent (Gemini 2.5 Flash) so the ADK Dev UI can show traces,
tool calls, and reasoning steps for the judges.

Run from project root:
    adk web services --a2a   # Dev UI at http://localhost:8000

The agent receives a message, calls the full pipeline as a tool, and
explains the equity-first results. The Dev UI trace shows:
  - Gemini reasoning about disaster response
  - Tool call to run_relieflink_pipeline
  - DisasterMonitorAgent, ParallelAgent, MatchOptimizerAgent execution
  - Equity-weighted match results
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so 'services' package is importable
# when adk web runs from the services/ directory
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from google.adk.agents import Agent


async def run_relieflink_pipeline_tool(state: str = "FL") -> dict:
    """
    Run the full ReliefLink disaster response pipeline.

    Executes:
    1. DisasterMonitorAgent — fetches live FEMA declarations + NOAA alerts
    2. ParallelAgent — ResourceScannerAgent + NeedMapperAgent run concurrently
    3. MatchOptimizerAgent — LoopAgent iteratively matches resources to needs by equity score

    Args:
        state: 2-letter US state abbreviation (default: FL for Florida/Tampa Bay demo)

    Returns:
        Pipeline results including matches, communities, resources, and metadata.
    """
    from services.relieflink_agents.orchestrator import _run_pipeline_async
    result = await _run_pipeline_async(state=state)

    disaster = result.get("disaster_event") or {}
    matches = result.get("matches", [])
    communities = result.get("communities", [])
    resources = result.get("resources", [])
    metadata = result.get("metadata", {})

    return {
        "status": result.get("status"),
        "disaster_id": disaster.get("disaster_id"),
        "disaster_type": disaster.get("disaster_type"),
        "severity": disaster.get("severity"),
        "active_alerts": len(disaster.get("active_alerts", [])),
        "resources_available": len(resources),
        "communities_affected": len(communities),
        "needs_identified": len(result.get("needs", [])),
        "matches_generated": len(matches),
        "iterations_run": metadata.get("iterations_run"),
        "converged": metadata.get("converged"),
        "top_matches": [
            {
                "resource_id": m.get("resource_id"),
                "need_id": m.get("need_id"),
                "equity_score": m.get("equity_score"),
            }
            for m in sorted(matches, key=lambda x: x.get("equity_score", 0), reverse=True)[:3]
        ],
    }


root_agent = Agent(
    name="ReliefLinkOrchestrator",
    model="gemini-2.5-flash",
    description="ReliefLink equity-first disaster resource coordination system using multi-agent AI.",
    instruction="""You are ReliefLink — a community-first disaster response coordination system built for HackUSF 2026.

Your mission: give community organizations, NGOs, and volunteer networks the coordination intelligence they need to route disaster relief resources to the most vulnerable people first — without waiting for slow government pipelines.

When a hurricane hits, community organizations are already on the ground before FEMA arrives. Red Cross chapters, VOAD volunteer networks, mutual aid groups, and local NGOs are coordinating disaster response — but right now they do it through Facebook groups and GroupMe texts. ReliefLink gives them a real coordination system.

When asked to run the pipeline, coordinate disaster response, or analyze relief needs:
1. Call the run_relieflink_pipeline_tool
2. Explain what each agent did in plain terms:
   - DisasterMonitorAgent detected the disaster from live FEMA and NOAA data
   - ResourceScanner and NeedMapper ran simultaneously — one finding available resources across all community channels, the other identifying which neighborhoods need help most
   - MatchOptimizer iterated until it found the best equity-weighted matches
3. Emphasize: the most vulnerable communities (highest CDC Social Vulnerability Index) are matched first — elderly residents, families with no cars, people in mobile homes — not the wealthiest neighborhoods with the best road access
4. This inverts the Cantillon Effect: resources normally flow to whoever is closest to infrastructure. ReliefLink routes to whoever needs it most.

Severity is determined by FEMA's own program declarations — not hardcoded:
- Individual Assistance declared → people lost homes (+3.0)
- Public Assistance declared → infrastructure destroyed (+2.5)
- Individual + Household declared → personal property destroyed (+2.5)
- Hazard Mitigation declared → serious long-term damage (+1.0)
- NOAA extreme alerts → pushes severity higher (+1.0)

A small storm that only triggers Hazard Mitigation gets severity ~1. Hurricane Milton with all programs activated + extreme NOAA alerts gets severity 10. This is live data from FEMA, not a hardcoded number.

Equity formula: equity_score = vulnerability_index × 0.6 + need_severity × 0.4

Always frame the impact around community organizations and NGOs gaining coordination power — reducing the 7-90 day delay to minutes, independent of slow government procurement.""",
    tools=[run_relieflink_pipeline_tool],
)
