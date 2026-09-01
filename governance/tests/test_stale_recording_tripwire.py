"""A recording made from edited prompt text must not replay silently.

`Recording.prompt_sha` documented itself as "a tripwire on the keying scheme" from the
day it was written, but nothing compared it. The cache key carries the prompt *version*
(`v1`), not the prompt text, so editing `shared.v1.md` or an agent brief in place leaves
the key resolving to a recording of the previous wording. Right agent, right evidence,
right model, plausible reasoning — produced by a prompt no longer in the repo.

The free tier allows 20 requests per day, so re-recording the full matrix costs more
than a day. That is the pressure under which a prompt gets edited and not re-recorded,
which is why this is a check and not a comment.
"""

from __future__ import annotations

import pytest
from conftest import make_evaluation

from governance.agents.llm_backed import opine_via_model
from governance.llm.errors import RecordingMissError, RecordingStaleError
from governance.llm.recording import (
    RecordingStore,
    build_recording,
    cache_key_for,
    prompt_fingerprint,
)
from governance.modes import CACHED
from governance.prompts.loader import build_prompt

AGENT = "risk"
SLUG = "gemini-3-6-flash"

RESPONSE = (
    '{"reasoning": "Exposure per erroneous approval rises from INR 1000 to INR 2500, '
    'a 2.5x multiplier, against 0 critical errors in the record.", '
    '"concerns": [], "verdict": "CONCUR", "confidence": 0.9}'
)


@pytest.fixture
def store(tmp_path):
    return RecordingStore(directory=tmp_path)


@pytest.fixture
def evaluation():
    return make_evaluation()


def _record(store: RecordingStore, prompt, *, prompt_sha: str | None = None):
    """Save a recording for `prompt`, optionally lying about which text produced it."""
    recording = build_recording(
        prompt, RESPONSE, "gemini-3.6-flash", provider="gemini", model_slug=SLUG
    )
    if prompt_sha is not None:
        recording = type(recording)(
            **{**{f: getattr(recording, f) for f in recording.__dataclass_fields__},
               "prompt_sha": prompt_sha}
        )
    store.save(recording)
    return recording


def test_a_matching_recording_replays(store, evaluation):
    """The happy path still works — the tripwire must not fire on good recordings."""
    prompt = build_prompt(AGENT, evaluation)
    _record(store, prompt)

    opinion = opine_via_model(AGENT, evaluation, CACHED, store=store, model_slug=SLUG)

    assert opinion.agent_name == AGENT


def test_an_edited_prompt_raises_rather_than_replaying(store, evaluation):
    """The bug this exists for: same key, different prompt text, silent replay."""
    prompt = build_prompt(AGENT, evaluation)
    _record(store, prompt, prompt_sha="0000stalesha0000")

    with pytest.raises(RecordingStaleError) as excinfo:
        opine_via_model(AGENT, evaluation, CACHED, store=store, model_slug=SLUG)

    assert excinfo.value.expected == "0000stalesha0000"
    assert excinfo.value.found == prompt_fingerprint(prompt)
    assert excinfo.value.cache_key == cache_key_for(prompt, SLUG)


def test_the_stale_error_is_not_retryable(store, evaluation):
    """Live mode's fallback reads `retryable`. Retrying cannot fix edited text.

    A stale recording is a repo state, not a transient condition — retrying would spend
    quota to arrive at the same mismatch.
    """
    prompt = build_prompt(AGENT, evaluation)
    _record(store, prompt, prompt_sha="0000stalesha0000")

    with pytest.raises(RecordingStaleError) as excinfo:
        opine_via_model(AGENT, evaluation, CACHED, store=store, model_slug=SLUG)

    assert excinfo.value.retryable is False


def test_the_message_says_what_to_do_about_it(store, evaluation):
    """Whoever hits this is mid-demo-prep and needs the fix, not a hash dump."""
    prompt = build_prompt(AGENT, evaluation)
    _record(store, prompt, prompt_sha="0000stalesha0000")

    with pytest.raises(RecordingStaleError, match="bump"):
        opine_via_model(AGENT, evaluation, CACHED, store=store, model_slug=SLUG)


def test_a_missing_recording_still_raises_a_miss_not_a_stale(store, evaluation):
    """The two failures are different and must stay distinguishable.

    A miss means record it. A stale means a prompt was edited. Collapsing them would
    send someone to spend quota re-recording when the real fix is reverting an edit.
    """
    with pytest.raises(RecordingMissError):
        opine_via_model(AGENT, evaluation, CACHED, store=store, model_slug=SLUG)
