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
from google.adk.agents import Agent


def run_relieflink_pipeline_tool(state: str = "FL") -> dict:
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
    from services.relieflink_agents.orchestrator import run_relieflink_pipeline
    result = run_relieflink_pipeline({"state": state})

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
    instruction="""You are ReliefLink — an equity-first disaster response coordination system built for HackUSF 2026.

Your mission: match scarce disaster relief resources to communities in need, prioritizing the most vulnerable communities first using CDC Social Vulnerability Index data.

When asked to run the pipeline, coordinate disaster response, or analyze relief needs:
1. Call the run_relieflink_pipeline_tool
2. Explain what each agent did:
   - DisasterMonitorAgent fetched live FEMA + NOAA data
   - ParallelAgent ran ResourceScanner + NeedMapper concurrently (FR-012)
   - MatchOptimizerAgent used LoopAgent to iteratively optimize matches by equity score
3. Highlight that vulnerable communities (high SVI score) are prioritized first — inverting the Cantillon Effect
4. Show the equity scores and explain why certain communities were matched first

Equity formula (MDR-03): equity_score = vulnerability_index × 0.6 + need_severity_normalized × 0.4

Always emphasize the social impact: reducing the 7-90 day resource matching delay to minutes.""",
    tools=[run_relieflink_pipeline_tool],
)
