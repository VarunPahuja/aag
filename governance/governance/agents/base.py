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
    """Guard for the modes this skeleton does not implement yet.

    Raising is deliberate. Quietly serving stub opinions when the caller asked for
    `cached` or `live` would make an unimplemented mode indistinguishable from a
    working one — the failure would surface as "the reasoning never changes," in front
    of whoever noticed first. Prompts and cached replay land 30 Aug, live mode 3 Sept
    (docs/DEADLINES.md).
    """
    if mode == STUB:
        return
    if mode in (CACHED, LIVE):
        raise NotImplementedError(
            f"{agent_name} agent has no {mode} implementation yet — "
            f"{CACHED} is due 30 Aug, {LIVE} 3 Sept (docs/DEADLINES.md). Use {STUB!r}."
        )
    raise ValueError(f"unknown governance mode {mode!r}")


def clamp_confidence(value: float) -> float:
    """Confidence is a 0.0-1.0 field on `AgentOpinion`; keep it there."""
    return max(0.0, min(1.0, value))
