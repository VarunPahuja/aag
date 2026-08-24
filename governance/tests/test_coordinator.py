"""The coordinator's contract with the backend, and the boundaries it must not cross."""

from __future__ import annotations

import pytest
from shared.constants import AUTONOMY_LADDER, rung_of
from shared.contracts import Recommendation
from shared.enums import Direction, OpinionVerdict, RecommendationStatus

from governance.agents import AGENT_NAMES
from governance.coordinator import recommend

ALL_FIXTURES = [
    "healthy_increase",
    "thin_sample",
    "active_drift",
    "recent_critical_error",
    "blocked_by_cooldown",
    "empty_history",
]


@pytest.fixture
def evaluation(request):
    """Parametrisation helper — resolves a fixture name to its value."""
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_returns_a_fully_populated_recommendation(evaluation):
    """Wed 26 Aug's done-condition: the backend gets a structurally correct Recommendation."""
    result = recommend(evaluation)

    assert isinstance(result, Recommendation)
    assert result.recommendation_id
    assert result.agent_id == evaluation.agent_id
    assert result.rationale
    assert result.generated_at is not None
    assert result.governance_mode == "stub"
    assert result.proposed_limit in AUTONOMY_LADDER
    assert result.proposed_rung == rung_of(result.proposed_limit)
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_every_agent_returns_exactly_one_opinion_in_a_stable_order(evaluation):
    result = recommend(evaluation)

    assert len(result.opinions) == len(AGENT_NAMES)
    assert tuple(o.agent_name for o in result.opinions) == AGENT_NAMES


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_status_is_always_pending(evaluation):
    """Governance cannot authorize its own recommendation — a human does (ADR-0004)."""
    assert recommend(evaluation).status is RecommendationStatus.PENDING


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_never_proposes_more_than_the_evidence_supports(evaluation):
    """The architectural claim, as an assertion: governance cannot ask for more authority
    than the trust engine's numbers already justify."""
    result = recommend(evaluation)
    assert result.proposed_limit <= max(evaluation.recommended_limit, evaluation.current_limit)


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_governance_never_reports_itself_as_clamped(evaluation):
    """Clamping is the backend's hard ceiling, not something this lane applies."""
    result = recommend(evaluation)
    assert result.clamped is False
    assert result.clamped_from is None


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_has_dissent_matches_the_opinions(evaluation):
    result = recommend(evaluation)
    objected = any(o.verdict is OpinionVerdict.OBJECT for o in result.opinions)
    assert result.has_dissent is objected


def test_clean_evidence_forwards_the_increase(healthy_increase):
    result = recommend(healthy_increase)

    assert result.has_dissent is False
    assert result.direction is Direction.INCREASE
    assert result.proposed_limit == healthy_increase.recommended_limit


def test_thin_sample_blocks_the_increase(thin_sample):
    """10/10 is not evidence. The performance agent objects and the ask is held."""
    result = recommend(thin_sample)

    assert result.has_dissent is True
    assert result.direction is Direction.HOLD
    assert result.proposed_limit == thin_sample.current_limit

    performance = next(o for o in result.opinions if o.agent_name == "performance")
    assert performance.verdict is OpinionVerdict.OBJECT
    assert "72.2%" in performance.reasoning  # the Wilson lower bound, not the 100%


def test_recent_critical_error_blocks_the_increase(recent_critical_error):
    result = recommend(recent_critical_error)

    assert result.direction is Direction.HOLD
    risk = next(o for o in result.opinions if o.agent_name == "risk")
    assert risk.verdict is OpinionVerdict.OBJECT


def test_dissent_cannot_soften_a_clawback(active_drift):
    """Dissent is one-directional: it can withhold authority, never restore it."""
    result = recommend(active_drift)

    assert result.direction is Direction.CLAWBACK
    assert result.proposed_limit == active_drift.recommended_limit
    assert result.proposed_limit < active_drift.current_limit


def test_dissent_is_surfaced_in_the_rationale_not_averaged_away(thin_sample):
    result = recommend(thin_sample)

    assert "Dissent from" in result.rationale
    assert "performance" in result.rationale


def test_eligible_but_cooled_down_stays_held(blocked_by_cooldown):
    """eligible_for_increase=True with direction=HOLD is a legal state, not a bug."""
    result = recommend(blocked_by_cooldown)

    assert result.direction is Direction.HOLD
    assert result.proposed_limit == blocked_by_cooldown.current_limit


def test_empty_history_produces_a_recommendation_rather_than_an_error(empty_history):
    result = recommend(empty_history)

    assert result.direction is Direction.HOLD
    abstained = [o for o in result.opinions if o.verdict is OpinionVerdict.ABSTAIN]
    assert abstained, "agents with no evidence should abstain, not guess"


@pytest.mark.parametrize("evaluation", ALL_FIXTURES, indirect=True)
def test_same_evaluation_gives_the_same_decision_every_run(evaluation):
    """Stub mode is deterministic. Only the id and timestamp may differ between runs."""
    first, second = recommend(evaluation), recommend(evaluation)

    assert first.direction is second.direction
    assert first.proposed_limit == second.proposed_limit
    assert first.confidence == second.confidence
    assert first.rationale == second.rationale
    assert [o.verdict for o in first.opinions] == [o.verdict for o in second.opinions]
