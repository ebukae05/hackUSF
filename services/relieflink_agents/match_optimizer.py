from __future__ import annotations

import logging
import math
from dataclasses import replace
from functools import wraps
from typing import Any

from .models_temp import Community, Match, MatchStatus, Need, Resource

EARTH_RADIUS_KM = 6371.0
MAX_PROXIMITY_DISTANCE_KM = 1000.0
QUALITY_STOP_THRESHOLD = 0.05
DEFAULT_MAX_ITERATIONS = 5

logger = logging.getLogger(__name__)
ROUTING_MODEL_NAME = "gemini-1.5-flash"
ROUTING_FALLBACK_PLAN = "Routing plan unavailable — dispatch manually"

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential
except ImportError:
    class _RetryStop:
        def __init__(self, attempts: int) -> None:
            self.attempts = attempts


    class _RetryWait:
        def __init__(self, *, multiplier: int, min: int, max: int) -> None:
            self.multiplier = multiplier
            self.min = min
            self.max = max


    def stop_after_attempt(attempts: int) -> _RetryStop:
        return _RetryStop(attempts)


    def wait_exponential(*, multiplier: int, min: int, max: int) -> _RetryWait:
        return _RetryWait(multiplier=multiplier, min=min, max=max)


    def before_sleep_log(logger: logging.Logger, level: int) -> Any:
        def _log(retry_state: Any) -> None:
            attempt_number = getattr(retry_state, "attempt_number", 0)
            outcome = getattr(retry_state, "outcome", None)
            exception = outcome.exception() if outcome is not None else "unknown error"
            logger.log(
                level,
                "Retrying routing plan generation after attempt %s failed: %s",
                attempt_number,
                exception,
            )

        return _log


    def retry(
        *,
        wait: _RetryWait,
        stop: _RetryStop,
        reraise: bool,
        before_sleep: Any | None = None,
    ) -> Any:
        def decorator(func: Any) -> Any:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                last_error: Exception | None = None
                for attempt in range(1, stop.attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:  # pragma: no cover - exercised via tests
                        last_error = exc
                        if attempt < stop.attempts:
                            if before_sleep is not None:
                                outcome = type(
                                    "_Outcome",
                                    (),
                                    {"exception": staticmethod(lambda exc=exc: exc)},
                                )()
                                retry_state = type(
                                    "_RetryState",
                                    (),
                                    {"attempt_number": attempt, "outcome": outcome},
                                )()
                                before_sleep(retry_state)
                if reraise and last_error is not None:
                    raise last_error
                return None

            return wrapper

        return decorator

class EventActions:
    """Minimal compatibility shim for local development without google-adk."""

    def __init__(self, escalate: bool = False) -> None:
        self.escalate = escalate


class Event:
    """Minimal compatibility shim for local development without google-adk."""

    def __init__(
        self,
        *,
        actions: EventActions | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.actions = actions or EventActions()
        self.data = data or {}


class BaseAgent:
    """Minimal compatibility shim for local development without google-adk."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, context: dict[str, Any]) -> Event:
        raise NotImplementedError


class LoopAgent:
    """Minimal compatibility shim mirroring the ADK LoopAgent shape."""

    def __init__(
        self,
        *,
        name: str,
        sub_agents: list[BaseAgent],
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        self.name = name
        self.sub_agents = sub_agents
        self.max_iterations = max_iterations

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        iterations = 0
        while iterations < self.max_iterations:
            iterations += 1
            context["iteration"] = iterations
            should_stop = False
            for sub_agent in self.sub_agents:
                event = sub_agent.run(context)
                if event.actions.escalate:
                    should_stop = True
                    break
            if should_stop:
                break
        context["iterations_run"] = iterations
        return context


def haversine_distance_km(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> float:
    """Return the great-circle distance in kilometers between two lat/lon points."""
    origin_lat, origin_lon = map(math.radians, origin)
    destination_lat, destination_lon = map(math.radians, destination)

    delta_lat = destination_lat - origin_lat
    delta_lon = destination_lon - origin_lon

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(origin_lat)
        * math.cos(destination_lat)
        * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def normalize_proximity_score(distance_km: float) -> float:
    """Convert distance into a 0-10 proximity score where 10 is closest."""
    clamped_distance = min(max(distance_km, 0.0), MAX_PROXIMITY_DISTANCE_KM)
    return 10 * (1 - (clamped_distance / MAX_PROXIMITY_DISTANCE_KM))


def calculate_equity_score(
    need: Need,
    community: Community,
    hub_location: tuple[float, float],
) -> float:
    """Calculate a weighted equity score for a resource allocation candidate.

    The score combines need severity, community vulnerability, and distance from a
    resource hub to the community. The proximity component is normalized to a
    0-10 scale where 10 represents the closest possible hub.

    Example:
        >>> need = Need(
        ...     id="n-1",
        ...     community_id="c-1",
        ...     resource_type="water",
        ...     quantity_needed=100,
        ...     severity=8,
        ... )
        >>> community = Community(
        ...     id="c-1",
        ...     zip_code="33620",
        ...     name="Tampa",
        ...     svi_score=6,
        ...     lat=28.0587,
        ...     lon=-82.4139,
        ...     population=1000,
        ... )
        >>> round(calculate_equity_score(need, community, (28.0587, -82.4139)), 2)
        7.8
    """
    if need.community_id != community.id:
        raise ValueError("need.community_id must match community.id")

    distance_km = haversine_distance_km(hub_location, (community.lat, community.lon))
    proximity_score = normalize_proximity_score(distance_km)
    return (
        (need.severity * 0.5)
        + (community.svi_score * 0.3)
        + (proximity_score * 0.2)
    )


def _build_routing_prompt(match: Match, community: Community) -> str:
    return (
        "Generate a concise natural-language disaster relief routing instruction. "
        f"Community: {community.name} ({community.zip_code}). "
        f"Coordinates: {community.lat}, {community.lon}. "
        f"Match resource id: {match.resource_id}. "
        f"Need id: {match.need_id}. "
        f"Quantity allocated: {match.quantity_allocated:g}. "
        "Return a single sentence with route, destination, and ETA."
    )


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=4),
    stop=stop_after_attempt(3),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _generate_routing_plan_with_retry(match: Match, community: Community) -> str:
    """Generate a routing plan with Gemini, retrying transient failures."""
    if genai is None:
        raise RuntimeError("google.generativeai is not installed")

    model = genai.GenerativeModel(ROUTING_MODEL_NAME)
    response = model.generate_content(_build_routing_prompt(match, community))
    text = getattr(response, "text", "") or ""
    plan = text.strip()
    if not plan:
        raise ValueError("Gemini returned an empty routing plan")
    return plan


def get_routing_plan(match: Match, community: Community) -> str:
    """Return a natural-language routing plan generated by Gemini 1.5 Flash."""
    try:
        return _generate_routing_plan_with_retry(match, community)
    except Exception as exc:
        logger.exception("Routing plan generation failed after retries: %s", exc)
        return ROUTING_FALLBACK_PLAN


def _match_identifier(match: Match) -> str:
    """Return the stable identifier used by re-optimization workflows."""
    return f"{match.resource_id}:{match.need_id}"


class _ScoringAgent(BaseAgent):
    """ADK-compatible sub-agent that scores and applies one allocation per loop."""

    def __init__(self, *, stop_threshold: float = QUALITY_STOP_THRESHOLD) -> None:
        super().__init__(name="ScoringAgent")
        self.stop_threshold = stop_threshold

    def run(self, context: dict[str, Any]) -> Event:
        resources: list[Resource] = context["resources"]
        needs: list[Need] = context["needs"]
        communities: dict[str, Community] = context["communities"]
        matches: list[Match] = context["matches"]
        previous_quality: float | None = context.get("allocation_quality")

        best_candidate: tuple[float, Resource, Need, Community] | None = None
        for resource in resources:
            if resource.quantity <= 0:
                continue
            for need in needs:
                if need.quantity_needed <= 0 or need.resource_type != resource.type:
                    continue
                community = communities.get(need.community_id)
                if community is None:
                    continue
                score = calculate_equity_score(
                    need=need,
                    community=community,
                    hub_location=resource.hub_location,
                )
                candidate = (score, resource, need, community)
                if best_candidate is None or score > best_candidate[0]:
                    best_candidate = candidate

        if best_candidate is None:
            context["stop_reason"] = "no_remaining_pairs"
            return Event(actions=EventActions(escalate=True), data=context)

        equity_score, resource, need, community = best_candidate
        quantity_allocated = min(resource.quantity, need.quantity_needed)
        resource.quantity -= quantity_allocated
        need.quantity_needed -= quantity_allocated

        match = Match(
            resource_id=resource.id,
            need_id=need.id,
            community_id=community.id,
            equity_score=equity_score,
            quantity_allocated=quantity_allocated,
            routing_plan="pending",
            status=MatchStatus.PENDING,
        )
        match.routing_plan = get_routing_plan(match, community)
        matches.append(match)

        current_quality = sum(item.equity_score for item in matches) / len(matches)
        context["allocation_quality"] = current_quality
        context["best_quality"] = max(context.get("best_quality", 0.0), current_quality)

        if previous_quality is not None and abs(previous_quality - current_quality) < self.stop_threshold:
            context["stop_reason"] = "quality_plateau"
            return Event(actions=EventActions(escalate=True), data=context)

        return Event(data=context)


class MatchOptimizer:
    """Allocate resources to community needs using an ADK-style loop agent."""

    def __init__(self, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> None:
        self.max_iterations = max_iterations
        self.scoring_agent = _ScoringAgent()
        self.agent = LoopAgent(
            name="MatchOptimizer",
            sub_agents=[self.scoring_agent],
            max_iterations=max_iterations,
        )
        self.allocation_quality: float = 0.0
        self._base_resources: list[Resource] = []
        self._base_needs: list[Need] = []
        self._base_communities: list[Community] = []
        self._committed_matches: list[Match] = []
        self._latest_matches: list[Match] = []

    def _run_optimization(
        self,
        resources: list[Resource],
        needs: list[Need],
        communities: list[Community],
    ) -> list[Match]:
        """Execute the loop agent and return sorted pending matches."""
        resource_pool = [replace(resource) for resource in resources]
        need_pool = [replace(need) for need in needs]
        community_map = {community.id: replace(community) for community in communities}
        context: dict[str, Any] = {
            "resources": resource_pool,
            "needs": need_pool,
            "communities": community_map,
            "matches": [],
            "allocation_quality": None,
            "best_quality": 0.0,
            "stop_reason": None,
        }

        final_context = self.agent.run(context)
        matches = sorted(
            final_context["matches"],
            key=lambda item: item.equity_score,
            reverse=True,
        )
        self.allocation_quality = (
            sum(match.equity_score for match in matches) / len(matches)
            if matches
            else 0.0
        )

        if (
            final_context.get("iterations_run", 0) >= self.max_iterations
            and final_context.get("stop_reason") != "quality_plateau"
        ):
            logger.warning(
                "MatchOptimizer reached the max iteration limit (%s) and returned a best-effort allocation.",
                self.max_iterations,
            )

        return matches

    def optimize(
        self,
        resources: list[Resource],
        needs: list[Need],
        communities: list[Community],
    ) -> list[Match]:
        """Return matches sorted by equity score descending.

        The optimizer iteratively scores all valid resource-need pairs, applies the
        highest-scoring allocation, and stops when quality improvement falls below
        the threshold or the configured iteration cap is reached.
        """
        self._base_resources = [replace(resource) for resource in resources]
        self._base_needs = [replace(need) for need in needs]
        self._base_communities = [replace(community) for community in communities]
        self._committed_matches = []
        self._latest_matches = self._run_optimization(resources, needs, communities)
        return [replace(match) for match in self._latest_matches]

    def reoptimize(
        self,
        accepted_match_ids: list[str],
        skipped_match_ids: list[str],
    ) -> list[Match]:
        """Re-run allocation after operator review of tentative matches.

        This method is triggered when dispatch operators accept or skip tentative
        matches from the previous optimization run. Accepted matches are locked in
        and keep consuming inventory; skipped matches are released so their resource
        quantity and unmet need return to the available pool. The optimizer then
        re-runs the full loop on the remaining unmatched resources and needs and
        returns a fresh set of pending matches for only those remaining pairs.
        """
        if not self._base_resources or not self._base_needs or not self._base_communities:
            raise ValueError("reoptimize requires a prior optimize() run")

        prior_matches = {
            _match_identifier(match): replace(match) for match in self._latest_matches
        }
        unknown_ids = sorted(
            set(accepted_match_ids).union(skipped_match_ids).difference(prior_matches)
        )
        if unknown_ids:
            raise ValueError(f"Unknown match ids for reoptimization: {', '.join(unknown_ids)}")

        accepted_ids = set(accepted_match_ids)
        skipped_ids = set(skipped_match_ids)
        if accepted_ids & skipped_ids:
            overlap = ", ".join(sorted(accepted_ids & skipped_ids))
            raise ValueError(f"Match ids cannot be both accepted and skipped: {overlap}")

        resource_pool = {resource.id: replace(resource) for resource in self._base_resources}
        need_pool = {need.id: replace(need) for need in self._base_needs}
        communities = [replace(community) for community in self._base_communities]

        committed_matches: list[Match] = []
        historical_skipped: list[Match] = []

        for match_id, match in prior_matches.items():
            if match_id in accepted_ids:
                accepted_match = replace(match, status=MatchStatus.ACCEPTED)
                committed_matches.append(accepted_match)
                resource_pool[match.resource_id].quantity -= match.quantity_allocated
                need_pool[match.need_id].quantity_needed -= match.quantity_allocated
            elif match_id in skipped_ids:
                historical_skipped.append(replace(match, status=MatchStatus.SKIPPED))

        remaining_resources = [
            resource for resource in resource_pool.values() if resource.quantity > 0
        ]
        remaining_needs = [
            need for need in need_pool.values() if need.quantity_needed > 0
        ]

        fresh_matches = self._run_optimization(
            resources=remaining_resources,
            needs=remaining_needs,
            communities=communities,
        )
        self._committed_matches = committed_matches + historical_skipped
        self._latest_matches = fresh_matches
        return [replace(match) for match in fresh_matches]
