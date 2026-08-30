"""The hard ceiling: deterministic code between a governance recommendation
and anything that can act on it (ADR-0003, ADR-0014).

Governance is advisory (`shared.contracts.Recommendation`'s docstring,
ADR-0001, ADR-0004) — a panel of LLM-backed agents proposes a limit, but
nothing here trusts that proposal on its own. `clamp_recommendation` is the
structural answer to "what if the LLM hallucinates a recommendation": plain,
pure, testable code, not another model call, sits between the proposal and
the agent's actual limit.
"""

from __future__ import annotations

from typing import NamedTuple


class ClampResult(NamedTuple):
    """A plain 3-tuple (final_limit, clamped, clamped_from) with names attached —
    unpacks positionally exactly as the task signature describes, while still
    being self-documenting at the call site."""

    final_limit: int
    clamped: bool
    clamped_from: int | None


def clamp_recommendation(proposed_limit: int, evidence_supported_limit: int) -> ClampResult:
    """Reduce `proposed_limit` to what the evidence actually supports.

    `evidence_supported_limit` is `TrustEvaluation.recommended_limit`
    (`shared/contracts.py`) — the trust engine's own ceiling, which
    `trust_engine.ladder.evaluate_ladder` already caps to at most one rung
    above the agent's current limit per evaluation
    (`trust/trust_engine/ladder.py`: `new_rung = min(current_rung + 1,
    MAX_RUNG)`). This function does not re-derive that cap independently — it
    has no `current_limit` input to derive it from, by design, since a
    Policy Engine ceiling based on stale state would be its own bug. Its one
    guarantee, and the only one it needs, is narrower and unconditional: the
    final limit never exceeds `evidence_supported_limit`, no matter what a
    governance panel proposed. Combined with the trust engine's own one-rung
    cap upstream, the practical effect is exactly "an increase moves at most
    one rung, regardless of what was proposed" — but that property is two
    independent, separately-tested guarantees composing, not one function
    reconstructing the other's job.

    The clamp is one-sided. A `proposed_limit` at or below
    `evidence_supported_limit` (a HOLD, a CLAWBACK, or an increase the
    evidence already covers) passes through unchanged — this is a ceiling,
    never a floor a low proposal gets pulled up to.

    Never silently clamps: `clamped` and `clamped_from` always say whether and
    from what a reduction happened, even though `final_limit` alone would let
    a careless caller reconstruct the same number without ever checking.
    """
    if proposed_limit <= evidence_supported_limit:
        return ClampResult(final_limit=proposed_limit, clamped=False, clamped_from=None)
    return ClampResult(
        final_limit=evidence_supported_limit, clamped=True, clamped_from=proposed_limit
    )
