"""The path an agent takes when its reasoning comes from a model rather than from code.

One function, `opine_via_model()`, shared by all four agents. The alternative — each
agent assembling its own prompt and parsing its own response — would give four places
for the validation boundary to drift apart, and the boundary is the thing keeping raw
model text out of the coordinator.

**The stub opinions are not a fallback for this path.** If a recording is missing or a
response fails validation, the error propagates. An agent that silently reverted to its
hand-written reasoning would produce a demo where the LLM appears to work and does not,
which is the exact failure the mode guard in `base.py` exists to prevent.

**Which provider serves an agent is read from the environment, per agent.** That is what
makes the recording lookup provider-aware: the cache key carries the model, so a panel
reconfigured from Gemini to Claude misses rather than replaying the wrong model's answer
(see `cache_key_for`).

Live mode is deliberately still closed here. The clients can reach their providers —
that is what the recording script uses — but routing an *agent* through one needs the
timeout, retry and cached-fallback rules due 3 Sept, and opening it early would mean a
demo that can fail in front of a panel.
"""

from __future__ import annotations

from shared.contracts import AgentOpinion, TrustEvaluation

from governance.llm.errors import RecordingStaleError
from governance.llm.recording import (
    RecordingStore,
    cache_key_for,
    prompt_fingerprint,
)
from governance.llm.registry import build_client
from governance.modes import CACHED, LIVE, STUB
from governance.prompts.loader import build_prompt
from governance.prompts.schema import parse_opinion


def opine_via_model(
    agent_name: str,
    evaluation: TrustEvaluation,
    mode: str,
    *,
    store: RecordingStore | None = None,
    model_slug: str | None = None,
) -> AgentOpinion:
    """Produce one agent's opinion from a recorded model response.

    Builds the same prompt the recording was made from, looks it up by a key that
    includes the model, and puts the response through `parse_opinion()` — the same
    validation a live response would face. Replaying without validating would let a
    recording made under an older schema quietly produce a malformed opinion.

    `model_slug` is resolved from the environment when not given. Constructing the
    client never needs a key, so this works with everything blank.
    """
    if mode != CACHED:
        raise ValueError(
            f"opine_via_model handles {CACHED!r} only, not {mode!r}. "
            f"{STUB!r} is handled in each agent module; {LIVE!r} is due 3 Sept."
        )

    prompt = build_prompt(agent_name, evaluation)
    slug = model_slug if model_slug is not None else build_client(agent_name).slug
    cache_key = cache_key_for(prompt, slug)
    recording = (store or RecordingStore()).load(cache_key)

    # `Recording.prompt_sha` calls itself a tripwire on the keying scheme. It was stored
    # and never compared, which made it a note rather than a check.
    #
    # The key covers agent, prompt version, model and evidence — not the prompt *text*.
    # Edit `shared.v1.md` or an agent brief without bumping to v2 and the key still
    # resolves, so cached mode replays reasoning produced by wording that is no longer
    # in the repo, and every visible signal looks correct.
    #
    # This matters more than it reads: the free tier is 20 requests a day, so a full
    # re-record costs longer than a day of wall-clock. That is exactly the pressure
    # under which someone tweaks a prompt and does not re-record.
    found = prompt_fingerprint(prompt)
    if recording.prompt_sha != found:
        raise RecordingStaleError(
            f"recording {cache_key!r} was made from different prompt text "
            f"(recorded {recording.prompt_sha}, current {found}). A prompt file was "
            f"edited without bumping its version. Bump the version and re-record, or "
            f"revert the edit — note the free tier allows 20 requests per day.",
            cache_key=cache_key,
            expected=recording.prompt_sha,
            found=found,
        )
    return parse_opinion(recording.response_text, agent_name)


def supports_mode(mode: str) -> bool:
    """Whether an agent can serve this mode today. Used by the guard in `base.py`."""
    return mode in (STUB, CACHED)
