"""What every governance agent is, and the two rules all four obey.

**Agents recommend; they never enforce.** An agent returns an `AgentOpinion` and
nothing else. It does not write to a database, mutate a policy, or change an autonomy
limit. That boundary is the project's central architectural claim — if an agent could
reach the enforcement path, "what happens when your LLM is wrong?" would have no
structural answer (docs/lanes/vc.md, ADR-0001).

**Agents read statistics; they never compute them.** Every number an agent reasons
about is already a field on the `TrustEvaluation` it was handed. The trust lane is the
only source of arithmetic. Deriving an accuracy rate here would mean two lanes could
disagree about the same evidence.
"""

from __future__ import annotations

from typing import Final, Protocol

from shared.contracts import AgentOpinion, TrustEvaluation

from governance.modes import CACHED, LIVE, STUB

AGENT_NAMES: Final[tuple[str, ...]] = ("risk", "performance", "compliance", "audit")


class GovernanceAgent(Protocol):
    """One agent's whole surface area: evidence in, an opinion out."""

    name: str

    def opine(self, evaluation: TrustEvaluation, mode: str) -> AgentOpinion: ...


def require_stub_mode(mode: str, agent_name: str) -> None:
    """Guard the hand-written reasoning path in each agent module.

    An agent module's `opine()` produces stub reasoning and only stub reasoning. Cached
    mode is served by `governance.agents.llm_backed.opine_via_model`, routed in the
    coordinator's node wrapper, so reaching this function with `cached` means something
    called an agent module directly and bypassed that routing.

    Raising is deliberate. Quietly serving stub opinions when the caller asked for
    `cached` or `live` would make the wrong path indistinguishable from the right one —
    the failure would surface as "the reasoning never changes," in front of whoever
    noticed first. Live mode is due 3 Sept (docs/DEADLINES.md).
    """
    if mode == STUB:
        return
    if mode == CACHED:
        raise NotImplementedError(
            f"{agent_name}.opine() serves {STUB!r} only. {CACHED!r} is served by "
            f"governance.agents.llm_backed.opine_via_model, which the coordinator routes "
            f"to — call recommend() rather than an agent module directly."
        )
    if mode == LIVE:
        raise NotImplementedError(
            f"{agent_name} agent has no {LIVE} implementation yet — due 3 Sept "
            f"(docs/DEADLINES.md). Use {STUB!r} or {CACHED!r}."
        )
    raise ValueError(f"unknown governance mode {mode!r}")


def clamp_confidence(value: float) -> float:
    """Confidence is a 0.0-1.0 field on `AgentOpinion`; keep it there."""
    return max(0.0, min(1.0, value))
