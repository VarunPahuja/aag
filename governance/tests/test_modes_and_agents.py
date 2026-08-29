"""Mode resolution, and the per-agent boundaries the coordinator tests don't isolate."""

from __future__ import annotations

from dataclasses import replace

import pytest
from conftest import make_evaluation
from shared.enums import Direction, OpinionVerdict

from governance.agents import AGENT_MODULES
from governance.agents.compliance import opine as compliance_opine
from governance.coordinator import recommend
from governance.llm.errors import RecordingMissError
from governance.modes import CACHED, DEFAULT_MODE, LIVE, STUB, resolve_mode


def test_default_mode_is_stub_not_cached():
    """An unset environment must not reach for fixtures that may not exist, and must not
    be one typo away from a live API call."""
    assert DEFAULT_MODE == STUB


def test_explicit_mode_beats_the_environment(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_MODE", LIVE)
    assert resolve_mode(STUB) == STUB


def test_environment_is_read_when_no_argument_is_given(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_MODE", CACHED)
    assert resolve_mode() == CACHED


def test_unset_environment_falls_back_to_stub(monkeypatch):
    monkeypatch.delenv("GOVERNANCE_MODE", raising=False)
    assert resolve_mode() == STUB


def test_unknown_mode_raises_rather_than_silently_stubbing(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_MODE", "stubb")
    with pytest.raises(ValueError, match="unknown GOVERNANCE_MODE"):
        resolve_mode()


def test_live_mode_still_fails_loudly(healthy_increase):
    """Serving stub opinions for an unimplemented mode would make a broken mode look
    exactly like a working one. Live is due 3 Sept."""
    with pytest.raises(NotImplementedError, match=LIVE):
        recommend(healthy_increase, mode=LIVE)


def test_cached_mode_without_a_recording_raises_rather_than_stubbing(healthy_increase):
    """Cached is implemented, so this is no longer NotImplementedError — but an
    unrecorded evaluation must still fail loudly rather than quietly serving the
    hand-written stub reasoning, which would look identical in the output."""
    with pytest.raises(RecordingMissError) as caught:
        recommend(healthy_increase, mode=CACHED)
    assert "governance.record" in str(caught.value)


@pytest.mark.parametrize("name", sorted(AGENT_MODULES))
def test_an_agent_module_called_directly_with_cached_says_where_cached_lives(
    name, healthy_increase
):
    """The routing is in the coordinator. Reaching an agent module with `cached` means
    something bypassed it, and the message has to say so rather than implying the mode
    is unbuilt."""
    with pytest.raises(NotImplementedError, match="llm_backed"):
        AGENT_MODULES[name].opine(healthy_increase, CACHED)


@pytest.mark.parametrize("name", sorted(AGENT_MODULES))
def test_every_agent_names_itself_consistently(name, healthy_increase):
    module = AGENT_MODULES[name]
    assert module.NAME == name
    assert module.opine(healthy_increase, STUB).agent_name == name


@pytest.mark.parametrize("name", sorted(AGENT_MODULES))
def test_every_agent_reports_confidence_in_range(name, healthy_increase):
    assert 0.0 <= AGENT_MODULES[name].opine(healthy_increase, STUB).confidence <= 1.0


def test_compliance_catches_a_broken_rung_limit_invariant():
    """TrustEvaluation is frozen and cannot enforce rung_of(limit) == rung itself, so a
    violation has to be caught by something before it reaches the Policy Engine."""
    healthy = make_evaluation(
        current_limit=500,
        recommended_limit=1000,
        direction=Direction.INCREASE,
        eligible_for_increase=True,
    )
    # 1000 is rung 1, so claiming rung 4 breaks the pairing.
    broken = replace(healthy, recommended_rung=4)

    opinion = compliance_opine(broken, STUB)
    assert opinion.verdict is OpinionVerdict.OBJECT
    assert any("recommended_rung" in c for c in opinion.concerns)


def test_compliance_objects_to_an_increase_that_contradicts_eligibility():
    """direction == INCREASE implies eligible_for_increase — the contract says so."""
    contradiction = make_evaluation(
        current_limit=500,
        recommended_limit=1000,
        direction=Direction.INCREASE,
        eligible_for_increase=False,
    )

    opinion = compliance_opine(contradiction, STUB)
    assert opinion.verdict is OpinionVerdict.OBJECT
    assert any("eligible_for_increase" in c for c in opinion.concerns)


def test_compliance_objects_to_an_off_ladder_limit():
    off_ladder = make_evaluation(
        current_limit=500,
        recommended_limit=750,
        direction=Direction.INCREASE,
        eligible_for_increase=True,
    )

    opinion = compliance_opine(off_ladder, STUB)
    assert opinion.verdict is OpinionVerdict.OBJECT
    assert any("not a rung" in c for c in opinion.concerns)
