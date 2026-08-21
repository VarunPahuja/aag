"""Tests for DecisionRecord's own behavior — before any of YOUR maths runs on it.

This file exists to prove one thing: what happens when an escalation is missing
recommended_action or human_ruling. It should be shown to Adhya as a spec, not just
run privately — every test name here is a sentence describing a rule her simulator
must follow.
"""

from __future__ import annotations

from shared.contracts import DecisionRecord
from shared.enums import Action

# --- normal decisions: not escalated, straightforward -------------------------------


def test_correct_approval_is_correct():
    d = DecisionRecord(
        decision_id="d1", sequence=1, invoice_id="i1", amount=500,
        action=Action.APPROVE, ground_truth=Action.APPROVE,
    )
    assert d.is_correct is True
    assert d.is_acted is True
    assert d.is_escalated is False


def test_wrong_approval_is_incorrect():
    d = DecisionRecord(
        decision_id="d2", sequence=2, invoice_id="i2", amount=500,
        action=Action.APPROVE, ground_truth=Action.REJECT,
    )
    assert d.is_correct is False


def test_wrong_approval_is_a_critical_error():
    """Approving something that should have been rejected — the serious kind."""
    d = DecisionRecord(
        decision_id="d3", sequence=3, invoice_id="i3", amount=500,
        action=Action.APPROVE, ground_truth=Action.REJECT,
    )
    assert d.is_critical_error is True
    assert d.is_noncritical_error is False


def test_wrong_rejection_is_noncritical_not_critical():
    """Rejecting something that should have been approved — annoying, not dangerous."""
    d = DecisionRecord(
        decision_id="d4", sequence=4, invoice_id="i4", amount=500,
        action=Action.REJECT, ground_truth=Action.APPROVE,
    )
    assert d.is_critical_error is False
    assert d.is_noncritical_error is True


# --- escalation: the core idea being tested -------------------------------------------


def test_escalation_is_not_counted_as_correct_or_incorrect():
    """The whole point: escalating is not a mistake, so it gets NEITHER answer."""
    d = DecisionRecord(
        decision_id="d5", sequence=5, invoice_id="i5", amount=500,
        action=Action.ESCALATE, ground_truth=Action.APPROVE,
        recommended_action=Action.APPROVE, human_ruling=Action.APPROVE,
    )
    assert d.is_correct is None       # not True, not False — the question doesn't apply
    assert d.is_escalated is True
    assert d.is_acted is False


def test_escalation_is_never_a_critical_error():
    d = DecisionRecord(
        decision_id="d6", sequence=6, invoice_id="i6", amount=500,
        action=Action.ESCALATE, ground_truth=Action.REJECT,
        recommended_action=Action.APPROVE, human_ruling=Action.REJECT,
    )
    assert d.is_critical_error is False


# --- properly filled escalations: agreement can be measured --------------------------


def test_escalation_with_both_fields_filled_shows_agreement():
    d = DecisionRecord(
        decision_id="d7", sequence=7, invoice_id="i7", amount=500,
        action=Action.ESCALATE, ground_truth=Action.APPROVE,
        recommended_action=Action.APPROVE, human_ruling=Action.APPROVE,
    )
    assert d.has_human_ruling is True
    assert d.human_agreed is True


def test_escalation_where_agent_hunch_was_wrong():
    """The agent leaned APPROVE, the human said REJECT — disagreement, correctly caught."""
    d = DecisionRecord(
        decision_id="d8", sequence=8, invoice_id="i8", amount=500,
        action=Action.ESCALATE, ground_truth=Action.REJECT,
        recommended_action=Action.APPROVE, human_ruling=Action.REJECT,
    )
    assert d.has_human_ruling is True
    assert d.human_agreed is False


# --- THE LANDMINE: what happens when the simulator forgets a field -------------------


def test_escalation_missing_recommended_action_has_no_agreement_signal():
    """If the simulator only sets action=ESCALATE and forgets recommended_action,
    this decision silently contributes NOTHING to human agreement. No crash, no
    error — just quietly excluded. This is the exact bug to watch for in Adhya's
    generator output.
    """
    d = DecisionRecord(
        decision_id="d9", sequence=9, invoice_id="i9", amount=500,
        action=Action.ESCALATE, ground_truth=Action.APPROVE,
        recommended_action=None,           # <-- forgotten
        human_ruling=Action.APPROVE,
    )
    assert d.has_human_ruling is False
    assert d.human_agreed is None


def test_escalation_missing_human_ruling_has_no_agreement_signal():
    """Same landmine, other field forgotten — e.g. a human just hasn't reviewed it yet."""
    d = DecisionRecord(
        decision_id="d10", sequence=10, invoice_id="i10", amount=500,
        action=Action.ESCALATE, ground_truth=Action.APPROVE,
        recommended_action=Action.APPROVE,
        human_ruling=None,                 # <-- not yet ruled on
    )
    assert d.has_human_ruling is False
    assert d.human_agreed is None


def test_escalation_missing_both_fields_has_no_agreement_signal():
    """The worst case: a bare ESCALATE with nothing else. Still doesn't crash —
    that's deliberate, since an unruled escalation is a normal, expected state
    (a human just hasn't gotten to it yet). The danger is only if EVERY escalation
    looks like this, which means the signal is missing everywhere, not just here.
    """
    d = DecisionRecord(
        decision_id="d11", sequence=11, invoice_id="i11", amount=500,
        action=Action.ESCALATE, ground_truth=Action.APPROVE,
    )
    assert d.has_human_ruling is False
    assert d.human_agreed is None
    assert d.is_correct is None    # still not treated as a mistake, that part still holds