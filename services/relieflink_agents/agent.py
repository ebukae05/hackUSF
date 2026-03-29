"""
ADK Dev UI entry point for ReliefLink.

Run from project root:
    adk web                          # Dev UI at http://localhost:8000
    adk run services.relieflink_agents  # Terminal mode

The root_agent is the ReliefLinkOrchestrator — a SequentialAgent that runs:
  1. DisasterMonitorAgent (FEMA + NOAA ingestion)
  2. ParallelAgent (ResourceScanner + NeedMapper concurrently)
  3. MatchOptimizerAgent (LoopAgent equity-weighted matching)
"""
from services.relieflink_agents.orchestrator import ReliefLinkOrchestrator

root_agent = ReliefLinkOrchestrator
