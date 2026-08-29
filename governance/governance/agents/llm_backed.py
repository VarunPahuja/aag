"""The path an agent takes when its reasoning comes from a model rather than from code.

One function, `opine_via_model()`, shared by all four agents. The alternative — each
agent assembling its own prompt and parsing its own response — would give four places
for the validation boundary to drift apart, and the boundary is the thing keeping raw
model text out of the coordinator.

**The stub opinions are not a fallback for this path.** If a recording is missing or a
response fails validation, the error propagates. An agent that silently reverts to its
hand-written reasoning would produce a demo where the LLM appears to work and does not,
which is the exact failure the mode guard in `base.py` exists to prevent.

Live mode is deliberately still closed here. The client can reach Gemini — that is what
the recording script uses — but routing an *agent* through it needs the timeout, retry
and cached-fallback rules due 3 Sept, and opening it early would mean a demo that can
fail in front of a panel.
"""

from __future__ import annotations

from shared.contracts import AgentOpinion, TrustEvaluation

from governance.llm.recording import RecordingStore
from governance.modes import CACHED, LIVE, STUB
from governance.prompts.loader import build_prompt
from governance.prompts.schema import parse_opinion


def opine_via_model(
    agent_name: str,
    evaluation: TrustEvaluation,
    mode: str,
    *,
    store: RecordingStore | None = None,
) -> AgentOpinion:
    """Produce one agent's opinion from a recorded model response.

    Builds the same prompt the recording was made from, looks it up by cache key, and
    puts the response through `parse_opinion()` — the same validation a live response
    would face. Replaying without validating would let a recording made under an older
    schema quietly produce a malformed opinion.
    """
    if mode != CACHED:
        raise ValueError(
            f"opine_via_model handles {CACHED!r} only, not {mode!r}. "
            f"{STUB!r} is handled in each agent module; {LIVE!r} is due 3 Sept."
        )

    prompt = build_prompt(agent_name, evaluation)
    recording = (store or RecordingStore()).load(prompt.cache_key)
    return parse_opinion(recording.response_text, agent_name)


def supports_mode(mode: str) -> bool:
    """Whether an agent can serve this mode today. Used by the guard in `base.py`."""
    return mode in (STUB, CACHED)
