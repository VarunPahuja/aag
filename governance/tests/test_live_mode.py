"""Live mode, and the fallback that makes it safe to demo.

The 3 Sept check in docs/DEADLINES.md is one sentence: *"Kill the network mid-run and a
valid recommendation still comes out."* These tests are that sentence, executed.

Nothing here touches the network. Live calls are driven through fake clients that fail
in the specific ways a real provider fails, which is the only way to test a network
failure deterministically.

The rule under test is that **the retry decision reads `retryable`, never the exception
type**. A test that asserted on class names would pass while the production rule was
matching on something else entirely.
"""

from __future__ import annotations

import pytest
from conftest import make_evaluation

from governance.agents.llm_backed import opine_with_provenance
from governance.coordinator import recommend
from governance.llm.errors import (
    GovernanceLLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMTransportError,
    RecordingMissError,
)
from governance.llm.recording import RecordingStore, build_recording
from governance.modes import CACHED, LIVE
from governance.prompts.loader import build_prompt

AGENT = "risk"
SLUG = "gemini-3-6-flash"

GOOD = (
    '{"reasoning": "Exposure per erroneous approval rises from INR 1000 to INR 2500, a '
    '2.5x multiplier, against 0 critical errors across 200 decisions.", '
    '"concerns": [], "verdict": "CONCUR", "confidence": 0.9}'
)
RECORDED = (
    '{"reasoning": "Recorded reasoning for exactly this evidence, made earlier by the '
    'same model.", "concerns": [], "verdict": "OBJECT", "confidence": 0.7}'
)


class FakeClient:
    """An LLMClient that fails on demand. Records the timeout it was handed."""

    provider = "gemini"
    model = "gemini-3.6-flash"

    def __init__(self, *, raises: Exception | None = None, text: str = GOOD, fail_times: int = 0):
        self._raises = raises
        self._text = text
        self._fail_times = fail_times
        self.calls = 0
        self.timeouts: list[float | None] = []

    def generate(self, prompt, *, timeout_s: float | None = None) -> str:
        self.calls += 1
        self.timeouts.append(timeout_s)
        if self._raises is not None and self.calls <= (self._fail_times or 10**6):
            raise self._raises
        return self._text

    @property
    def has_key(self) -> bool:
        return True

    @property
    def slug(self) -> str:
        return SLUG


@pytest.fixture
def evaluation():
    return make_evaluation()


@pytest.fixture
def store(tmp_path, evaluation):
    """A store holding a recording for this evidence — the fallback that must exist."""
    s = RecordingStore(directory=tmp_path)
    s.save(
        build_recording(
            build_prompt(AGENT, evaluation),
            RECORDED,
            "gemini-3.6-flash",
            provider="gemini",
            model_slug=SLUG,
        )
    )
    return s


@pytest.fixture
def use(monkeypatch):
    """Point the live path at a fake client."""

    def _use(client):
        monkeypatch.setattr("governance.agents.llm_backed.build_client", lambda _n: client)
        return client

    return _use


def test_a_working_live_call_is_not_a_fallback(evaluation, store, use):
    client = use(FakeClient())

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert result.fell_back is False
    assert result.opinion.verdict.value == "CONCUR"   # the live text, not the recording
    assert client.calls == 1


def test_the_network_dying_still_produces_an_opinion(evaluation, store, use):
    """The 3 Sept check, at the level of one agent."""
    use(FakeClient(raises=LLMTransportError("connection refused")))

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert result.fell_back is True
    assert result.opinion.verdict.value == "OBJECT"   # the recording, not the live text
    assert "LLMTransportError" in result.reason


def test_a_retryable_failure_is_retried_once_then_falls_back(evaluation, store, use):
    client = use(FakeClient(raises=LLMRateLimitError("429")))

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert client.calls == 2, "a retryable failure should be retried exactly once"
    assert result.fell_back is True


def test_a_retry_that_succeeds_is_not_a_fallback(evaluation, store, use):
    client = use(FakeClient(raises=LLMTransportError("blip"), fail_times=1))

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert client.calls == 2
    assert result.fell_back is False
    assert result.opinion.verdict.value == "CONCUR"


def test_a_non_retryable_failure_is_not_retried(evaluation, store, use):
    """Retrying a missing key spends the deadline to reach the same failure."""
    client = use(FakeClient(raises=LLMAuthError("key is empty")))

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert client.calls == 1
    assert result.fell_back is True


def test_the_retry_rule_reads_retryable_not_the_exception_type(evaluation, store, use):
    """A brand-new error class gets the right behaviour by declaring `retryable`.

    This is the property that keeps the rule from rotting: nothing anywhere matches on
    class names, so a subclass added later cannot be quietly left out of a tuple.
    """

    class NovelTransientError(GovernanceLLMError):
        retryable = True

    class NovelPermanentError(GovernanceLLMError):
        retryable = False

    transient = use(FakeClient(raises=NovelTransientError("never seen before")))
    opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)
    assert transient.calls == 2, "retryable=True should be retried without naming the class"

    permanent = use(FakeClient(raises=NovelPermanentError("never seen before")))
    opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)
    assert permanent.calls == 1, "retryable=False should not be retried"


def test_an_unparseable_live_response_falls_back_and_is_not_retried(evaluation, store, use):
    """Constrained decoding already guarantees shape, so asking again is the least
    likely thing to change it."""
    client = use(FakeClient(text="not json at all"))

    result = opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert client.calls == 1
    assert result.fell_back is True
    assert "failed validation" in result.reason


def test_live_uses_the_short_deadline_not_the_recording_one(evaluation, store, use):
    """A panel will not wait two minutes to discover the network is down."""
    from governance.llm.base import DEFAULT_TIMEOUT_S, LIVE_TIMEOUT_S

    client = use(FakeClient())
    opine_with_provenance(AGENT, evaluation, LIVE, store=store, model_slug=SLUG)

    assert client.timeouts == [LIVE_TIMEOUT_S]
    assert LIVE_TIMEOUT_S < DEFAULT_TIMEOUT_S


def test_no_recording_to_fall_back_to_names_both_failures(evaluation, tmp_path, use):
    """"No recording" alone would send someone to re-record when the network was the
    problem."""
    use(FakeClient(raises=LLMTransportError("connection refused")))
    empty = RecordingStore(directory=tmp_path)

    with pytest.raises(RecordingMissError) as caught:
        opine_with_provenance(AGENT, evaluation, LIVE, store=empty, model_slug=SLUG)

    message = str(caught.value)
    assert "live call failed" in message
    assert "connection refused" in message
    assert "governance.record" in message


@pytest.fixture
def panel_store(tmp_path, evaluation, monkeypatch):
    """Recordings for all four agents, wired in as the default store.

    `RecordingStore()` is patched rather than passed, because `recommend()` deliberately
    exposes no store parameter — the coordinator is the public path and must not grow a
    test-only argument.
    """
    from governance.agents import AGENT_NAMES

    store = RecordingStore(directory=tmp_path)
    for name in AGENT_NAMES:
        store.save(
            build_recording(
                build_prompt(name, evaluation),
                RECORDED,
                "gemini-3.6-flash",
                provider="gemini",
                model_slug=SLUG,
            )
        )
    monkeypatch.setattr("governance.agents.llm_backed.RecordingStore", lambda: store)
    return store


def test_a_fallback_recommendation_does_not_claim_to_be_live(
    evaluation, panel_store, monkeypatch
):
    """The whole reason the flag is threaded back to the coordinator.

    A recommendation that said `live` when recordings answered would be a demo that
    looks healthy and isn't — the exact failure this lane exists to prevent.
    """
    monkeypatch.setattr(
        "governance.agents.llm_backed.build_client",
        lambda _n: FakeClient(raises=LLMTransportError("network down")),
    )

    recommendation = recommend(evaluation, LIVE)

    assert recommendation.governance_mode == f"{LIVE}+{CACHED}"
    assert "Live call failed" in recommendation.rationale


def test_a_clean_live_run_says_live(evaluation, panel_store, monkeypatch):
    """The other half: no fallback, no qualifier on the mode."""
    monkeypatch.setattr(
        "governance.agents.llm_backed.build_client", lambda _n: FakeClient()
    )

    recommendation = recommend(evaluation, LIVE)

    assert recommendation.governance_mode == LIVE
    assert "Live call failed" not in recommendation.rationale


def test_killing_the_network_mid_run_still_produces_a_valid_recommendation(
    evaluation, panel_store, monkeypatch
):
    """docs/DEADLINES.md, 3 Sept, verbatim: kill the network mid-run and a valid
    recommendation still comes out.

    Mid-run, not before it: two agents answer live, then the network dies under the
    other two. The recommendation must still be complete — four opinions, a real
    direction — and must say that it is partly recorded.
    """
    from governance.agents import AGENT_NAMES

    served: list[str] = []

    def client_for(agent_name: str):
        served.append(agent_name)
        if len(served) <= 2:
            return FakeClient()
        return FakeClient(raises=LLMTransportError("network went away mid-run"))

    monkeypatch.setattr("governance.agents.llm_backed.build_client", client_for)

    recommendation = recommend(evaluation, LIVE)

    assert len(recommendation.opinions) == len(AGENT_NAMES)
    assert recommendation.direction is not None
    assert recommendation.governance_mode == f"{LIVE}+{CACHED}"
    assert recommendation.status.value == "PENDING"
