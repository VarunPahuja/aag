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

**Live mode falls back to its recording, and says so.** A live call that fails, times
out, or returns something unparseable is served from the recording for the same
evidence. This is the one fallback in this lane, and it is not silent: the agent's name
is reported back to the coordinator, which marks the whole recommendation
`live+cached` rather than `live`. A recommendation that claims to be live when a
recording answered would be exactly the failure this lane exists to prevent.

Falling back to a *recording* is not the same as falling back to stub text. The
recording is a real model response to this same evidence, made by the same model; stub
text is hand-written and would make an LLM appear to work when it did not.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import AgentOpinion, TrustEvaluation

from governance.llm.base import LIVE_TIMEOUT_S, LLMClient
from governance.llm.errors import (
    GovernanceLLMError,
    RecordingMissError,
    RecordingStaleError,
)
from governance.llm.recording import (
    RecordingStore,
    cache_key_for,
    prompt_fingerprint,
)
from governance.llm.registry import build_client
from governance.modes import CACHED, LIVE, STUB
from governance.prompts.loader import Prompt, build_prompt
from governance.prompts.schema import OpinionParseError, parse_opinion


@dataclass(frozen=True, slots=True)
class ModelOpinion:
    """One agent's opinion, plus whether live mode had to fall back to get it.

    The flag exists so the coordinator can label the recommendation honestly. It is not
    an error channel — `reason` is filled in on a successful fallback, and the failure
    that caused it has already been handled.
    """

    opinion: AgentOpinion
    fell_back: bool = False
    reason: str = ""


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
    if mode not in (CACHED, LIVE):
        raise ValueError(
            f"opine_via_model handles {CACHED!r} and {LIVE!r} only, not {mode!r}. "
            f"{STUB!r} is handled in each agent module."
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


def opine_with_provenance(
    agent_name: str,
    evaluation: TrustEvaluation,
    mode: str,
    *,
    store: RecordingStore | None = None,
    model_slug: str | None = None,
    timeout_s: float = LIVE_TIMEOUT_S,
) -> ModelOpinion:
    """One agent's opinion, and whether live mode had to fall back to produce it.

    In `cached` mode this is `opine_via_model` with `fell_back=False`.

    In `live` mode it calls the provider and, on any failure, serves the recording for
    the same evidence instead. **The retry decision reads `retryable`, never the
    exception type** — that is why every error in this lane carries the flag. A new
    error class gets the right behaviour by declaring it, rather than by being added to
    a tuple somewhere that nobody remembers to update.

    - `retryable=True` (transport, rate limit) — one retry, then the recording.
    - `retryable=False` (auth, refusal, provider missing) — straight to the recording.
      Retrying a missing key spends the deadline to reach the same failure.
    - An unparseable live response is treated the same way: the recording for this
      evidence is a validated response to the same question, which the live text was
      not.

    If the recording is also missing, the miss is raised — with the live failure named
    in it, because "no recording" alone would send someone to re-record when the real
    problem was the network.
    """
    if mode == CACHED:
        return ModelOpinion(
            opine_via_model(agent_name, evaluation, mode, store=store, model_slug=model_slug)
        )
    if mode != LIVE:
        raise ValueError(f"opine_with_provenance handles {CACHED!r} and {LIVE!r}, not {mode!r}.")

    prompt = build_prompt(agent_name, evaluation)
    client = build_client(agent_name)
    slug = model_slug if model_slug is not None else client.slug

    opinion, failure = _try_live(client, prompt, agent_name, timeout_s)
    if opinion is not None:
        return ModelOpinion(opinion)

    try:
        opinion = opine_via_model(agent_name, evaluation, CACHED, store=store, model_slug=slug)
    except RecordingMissError as miss:
        raise RecordingMissError(
            f"live call failed ({failure}) and there is no recording to fall back to. "
            f"{miss}",
            cache_key=miss.cache_key,
        ) from miss

    return ModelOpinion(opinion, fell_back=True, reason=failure)


def _try_live(
    client: LLMClient, prompt: Prompt, agent_name: str, timeout_s: float
) -> tuple[AgentOpinion | None, str]:
    """Attempt the live call, retrying once if the failure says it is worth retrying.

    Returns `(opinion, "")` on success or `(None, why)` on failure. `why` is carried
    into the recommendation's rationale, so it is written to be read by a human deciding
    whether to trust the result.
    """
    failure = ""
    for attempt in (1, 2):
        try:
            return parse_opinion(client.generate(prompt, timeout_s=timeout_s), agent_name), ""
        except OpinionParseError as exc:
            # Not retried. Constrained decoding already guarantees the shape, so a
            # validation failure is the model refusing or truncating, and asking the
            # same question again is the least likely thing to change it.
            return None, f"live response failed validation: {exc}"
        except GovernanceLLMError as exc:
            failure = f"{type(exc).__name__}: {exc}"
            if not exc.retryable or attempt == 2:
                return None, failure
    return None, failure


def supports_mode(mode: str) -> bool:
    """Whether an agent can serve this mode today. Used by the guard in `base.py`."""
    return mode in (STUB, CACHED, LIVE)
