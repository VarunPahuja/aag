"""`clamp_recommendation` — the hard ceiling between a governance proposal and
an agent's actual limit."""

from __future__ import annotations

from shared.constants import limit_of

from app.policy.ceiling import clamp_recommendation


def test_proposal_within_evidence_passes_through_unclamped():
    result = clamp_recommendation(proposed_limit=limit_of(2), evidence_supported_limit=limit_of(3))
    assert result.final_limit == limit_of(2)
    assert result.clamped is False
    assert result.clamped_from is None


def test_proposal_exceeding_evidence_is_clamped_down():
    # The fixture story in app/fixtures/recommendations.py: governance's panel
    # read rung-4 headroom, the trust engine only supported rung 3.
    result = clamp_recommendation(proposed_limit=limit_of(4), evidence_supported_limit=limit_of(3))
    assert result.final_limit == limit_of(3)
    assert result.clamped is True
    assert result.clamped_from == limit_of(4)


def test_proposal_exactly_at_evidence_is_not_clamped():
    result = clamp_recommendation(proposed_limit=limit_of(3), evidence_supported_limit=limit_of(3))
    assert result.final_limit == limit_of(3)
    assert result.clamped is False
    assert result.clamped_from is None


def test_clamp_never_pulls_a_low_proposal_up_to_the_ceiling():
    # A CLAWBACK or HOLD proposal below the evidence ceiling is not raised to
    # meet it — this is a ceiling, never a floor.
    result = clamp_recommendation(proposed_limit=limit_of(0), evidence_supported_limit=limit_of(3))
    assert result.final_limit == limit_of(0)
    assert result.clamped is False
    assert result.clamped_from is None


def test_clamping_never_silent_the_fact_is_always_recorded():
    clamped_result = clamp_recommendation(proposed_limit=10000, evidence_supported_limit=5000)
    unclamped_result = clamp_recommendation(proposed_limit=5000, evidence_supported_limit=5000)
    assert clamped_result.clamped is True and clamped_result.clamped_from == 10000
    assert unclamped_result.clamped is False and unclamped_result.clamped_from is None


def test_result_unpacks_as_a_plain_tuple():
    final_limit, clamped, clamped_from = clamp_recommendation(
        proposed_limit=limit_of(4), evidence_supported_limit=limit_of(3)
    )
    assert (final_limit, clamped, clamped_from) == (limit_of(3), True, limit_of(4))


def test_clamp_is_deterministic_same_inputs_same_output():
    first = clamp_recommendation(proposed_limit=7000, evidence_supported_limit=5000)
    second = clamp_recommendation(proposed_limit=7000, evidence_supported_limit=5000)
    assert first == second
