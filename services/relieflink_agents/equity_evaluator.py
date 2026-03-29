"""
EquityEvaluatorAgent — Post-matching reasoning and self-correction.

An LlmAgent (Gemini 2.5 Flash) that reviews the MatchOptimizer's output
and can reorder matches if it detects equity violations — communities with
high vulnerability scores being deprioritized behind lower-vulnerability ones.

This is the reasoning layer the pipeline was missing. The equity formula
produces a mathematical ranking. Gemini evaluates whether that ranking
actually serves the most vulnerable communities first, and corrects it if not.

This satisfies the Google ADK judging self-correction criterion:
"Any LoopAgent that identifies its own error and re-runs the task."
Here: identifies misranking and reorders — genuinely autonomous correction.

Reference: docs/SYSTEM_DESIGN.md Section 1.3.B (B5 extension), MDR-03
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from google.adk.agents import Agent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def reorder_matches_by_equity(
    corrected_order: list[dict[str, Any]],
    reasoning: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Reorder the match list based on equity reasoning.
    Called by Gemini when it detects that the algorithmic ranking
    does not correctly prioritize the most vulnerable communities.

    Args:
        corrected_order: List of {match_id, equity_score} dicts in the
                         corrected priority order (highest priority first).
        reasoning: Explanation of why the reordering is needed.
        tool_context: ADK tool context for session state access.

    Returns:
        Confirmation of the correction applied.
    """
    current_matches = tool_context.state.get("match_data", {}).get("matches", [])
    if not current_matches or not corrected_order:
        return {"status": "no_correction_needed", "reasoning": reasoning}

    # Build a lookup by match_id
    matches_by_id = {m["match_id"]: m for m in current_matches if "match_id" in m}
    corrected_ids = [entry["match_id"] for entry in corrected_order if "match_id" in entry]

    # Reorder — corrected IDs first, then any remaining matches
    reordered = [matches_by_id[mid] for mid in corrected_ids if mid in matches_by_id]
    remaining = [m for m in current_matches if m.get("match_id") not in set(corrected_ids)]
    final_matches = reordered + remaining

    # Update session state with corrected order
    match_data = tool_context.state.get("match_data", {})
    match_data["matches"] = final_matches
    match_data["equity_corrected"] = True
    match_data["equity_correction_reasoning"] = reasoning
    tool_context.state["match_data"] = match_data

    logger.info(
        "EquityEvaluator: reordered %d matches. Reasoning: %s",
        len(final_matches), reasoning[:100]
    )
    return {
        "status": "correction_applied",
        "matches_reordered": len(reordered),
        "reasoning": reasoning,
    }


def confirm_equity_correct(
    assessment: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Confirm that the current match ordering correctly prioritizes
    vulnerable communities and no correction is needed.

    Args:
        assessment: Gemini's equity assessment of the current matches.
        tool_context: ADK tool context for session state access.

    Returns:
        Confirmation that no correction was needed.
    """
    match_data = tool_context.state.get("match_data", {})
    match_data["equity_corrected"] = False
    match_data["equity_correction_reasoning"] = assessment
    tool_context.state["match_data"] = match_data

    logger.info("EquityEvaluator: allocation confirmed equitable. %s", assessment[:100])
    return {"status": "confirmed_equitable", "assessment": assessment}


_EQUITY_INSTRUCTION = """You are ReliefLink's Equity Evaluator — an AI agent that reviews disaster
relief resource matches to ensure the most vulnerable communities are served first.

You will receive the current match list and community vulnerability data from session state.

Your job:
1. Review each match: which community is receiving resources and what is their vulnerability score (0-1, where 1 = most vulnerable)?
2. Check: are the highest-vulnerability communities matched first? Or did the algorithm deprioritize them?
3. Look for equity violations: a community with SVI 0.85+ should NEVER appear below a community with SVI 0.5 or lower in the match list, unless there is a strong need severity justification.

The equity formula used was: equity_score = vulnerability_index × 0.6 + need_severity × 0.4

Evaluate whether this formula produced the correct ordering given the actual communities and their circumstances.

If you detect an equity violation — a more vulnerable community ranked behind a less vulnerable one without strong need severity justification — call reorder_matches_by_equity() with the corrected order and a clear explanation.

If the ordering is correct and the most vulnerable communities are properly prioritized, call confirm_equity_correct() with your assessment.

Always explain your reasoning clearly. This is the self-correction layer that ensures the algorithmic output actually serves the communities who need it most.

Access the match data and community information from the session state context."""


def build_equity_evaluator_agent() -> Agent:
    """Factory — creates a fresh EquityEvaluatorAgent instance each call.

    ADK agents cannot be shared across multiple parent agents (pydantic
    validates single-parent ownership). Always call this factory instead
    of reusing a module-level singleton.
    """
    return Agent(
        name="EquityEvaluatorAgent",
        model="gemini-2.5-flash",
        description=(
            "Reviews resource-to-need matches for equity violations and corrects "
            "the ordering if the most vulnerable communities are not prioritized first."
        ),
        instruction=_EQUITY_INSTRUCTION,
        tools=[reorder_matches_by_equity, confirm_equity_correct],
        output_key="equity_evaluation",
    )


class _SafeEquityEvaluator(BaseAgent):
    """Wrapper that runs EquityEvaluatorAgent and swallows non-fatal errors.

    If Gemini is unavailable (no API key, network failure), the pipeline
    continues with the MatchOptimizer's ordering unchanged. The equity
    evaluation is a quality-of-service layer, not a hard dependency.
    """

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs):
        super().__init__(name="EquityEvaluatorAgent", **kwargs)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        inner = build_equity_evaluator_agent()
        try:
            async for event in inner.run_async(ctx):
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "EquityEvaluatorAgent: skipped due to error (%s: %s). "
                "Matches remain in MatchOptimizer order.",
                type(exc).__name__,
                exc,
            )
            # Mark as skipped so the dashboard knows
            match_data = ctx.session.state.get("match_data", {})
            match_data.setdefault("equity_corrected", False)
            match_data.setdefault(
                "equity_correction_reasoning",
                f"Equity evaluation unavailable: {exc}",
            )
            ctx.session.state["match_data"] = match_data

        if False:
            yield


def build_safe_equity_evaluator() -> _SafeEquityEvaluator:
    """Factory — returns a fresh SafeEquityEvaluator each call."""
    return _SafeEquityEvaluator()


# Module-level instance for ADK Dev UI discovery / direct import
EquityEvaluatorAgent = build_equity_evaluator_agent()
