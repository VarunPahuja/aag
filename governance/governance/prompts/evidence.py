"""Render a `TrustEvaluation` into the evidence block a prompt receives.

Two properties this module has to hold, both load-bearing:

**It computes nothing.** Every number below is copied from a field. No rate is derived,
no bound is recalculated, no threshold is applied. If this file ever needs arithmetic
over decision counts, the work belongs in the trust lane instead — two lanes computing
the same statistic is two lanes that can disagree about the same evidence
(docs/lanes/vc.md, ADR-0001).

**It is deterministic.** The same evaluation renders to the same string, byte for byte,
every time. Cached mode keys on a hash of this text, so a stray timestamp or a
set-ordering would mean a fixture recorded on Tuesday never matches on Wednesday and
the "unplug the wifi" demo quietly starts making live calls.
"""

from __future__ import annotations

import hashlib

from shared.constants import AUTONOMY_LADDER, MAX_RUNG
from shared.contracts import ProportionResult, TrustEvaluation
from shared.reason_codes import describe


def render_evidence(evaluation: TrustEvaluation) -> str:
    """The full evidence block, identical for all four agents.

    Every agent sees everything. Narrowing the evidence per agent would make their
    disagreements an artifact of what each was shown rather than of how each reasoned,
    and disagreement is the output this lane exists to produce.
    """
    drift = evaluation.drift
    lines = [
        "## Agent under evaluation",
        f"- agent_id: {evaluation.agent_id}",
        f"- state: {evaluation.state.value}",
        f"- trust_score: {evaluation.trust_score:.1f} / 100",
        "",
        "## Autonomy position",
        (
            f"- current limit: INR {evaluation.current_limit}"
            f" (rung {evaluation.current_rung} of {MAX_RUNG})"
        ),
        (
            f"- proposed limit: INR {evaluation.recommended_limit}"
            f" (rung {evaluation.recommended_rung})"
        ),
        f"- direction proposed by the trust engine: {evaluation.direction.value}",
        f"- eligible_for_increase: {evaluation.eligible_for_increase}",
        f"- decisions since the last change: {evaluation.decisions_since_last_change}",
        f"- ladder: {', '.join(f'INR {rung}' for rung in AUTONOMY_LADDER)}",
        "",
        "## Decision volume",
        f"- total: {evaluation.total_decisions}",
        f"- acted autonomously: {evaluation.acted_decisions}",
        (
            f"- escalated to a human: {evaluation.escalated_decisions}"
            f" ({evaluation.ruled_escalations} ruled on)"
        ),
        "",
        "## Accuracy",
        _render_proportion("accuracy", evaluation.accuracy),
        _render_proportion("human agreement", evaluation.human_agreement),
        _render_proportion("utilization", evaluation.utilization),
        "",
        "## Errors",
        (
            "- critical (approved something that should have been rejected):"
            f" {evaluation.critical_errors}"
        ),
        f"- critical in the recent window: {evaluation.critical_errors_in_recent_window}",
        f"- non-critical: {evaluation.noncritical_errors}",
        f"- critical error rate: {evaluation.critical_error_rate:.4f}",
        "",
        "## Drift",
        f"- severity: {drift.severity.value}",
        f"- detected: {drift.detected}",
        f"- recent accuracy: {_opt_pct(drift.recent_accuracy)} over {drift.recent_n} decisions",
        (
            f"- baseline accuracy: {_opt_pct(drift.baseline_accuracy)}"
            f" over {drift.baseline_n} decisions"
        ),
        f"- drop: {_opt_pp(drift.drop_pp)}",
        f"- z: {_opt_num(drift.z_statistic)}, p: {_opt_num(drift.p_value)}",
        f"- critical errors in the drift window: {drift.critical_errors_in_window}",
        f"- underpowered: {drift.underpowered}",
        "",
        "## Trust score composition",
    ]

    if evaluation.components:
        for component in evaluation.components:
            availability = "available" if component.available else "UNAVAILABLE"
            lines.append(
                f"- {component.name}: value {_opt_num(component.value)}, "
                f"nominal weight {component.nominal_weight:.2f}, "
                f"effective weight {component.effective_weight:.2f} ({availability})"
            )
    else:
        lines.append("- no component breakdown supplied")

    lines.append(f"- weights renormalised: {evaluation.weights_renormalised}")
    lines.append("")
    lines.append("## Reason codes from the trust engine")

    if evaluation.reason_codes:
        # describe() generates the sentence from the code. Never the reverse — a
        # hand-written explanation is one that can contradict the code it explains.
        for code in evaluation.reason_codes:
            # describe() takes a list, not a code. Passing a bare string iterates its
            # characters and renders "[E] [V] [I] ..." — well-formed, and nonsense.
            lines.append(f"- {code}: {describe([code])}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def evidence_fingerprint(evaluation: TrustEvaluation) -> str:
    """A stable id for one evidence block — the cache key for recorded responses.

    Hashing the rendered text rather than the object means a fixture is keyed by
    exactly what the model was shown. Change the renderer and old fixtures stop
    matching, which is the correct outcome: they were recorded against a different
    question.
    """
    return hashlib.sha256(render_evidence(evaluation).encode("utf-8")).hexdigest()[:16]


def _render_proportion(label: str, proportion: ProportionResult | None) -> str:
    if proportion is None or not proportion.has_evidence:
        return f"- {label}: no evidence (0 trials)"
    point = "n/a" if proportion.point is None else f"{proportion.point:.1%}"
    return (
        f"- {label}: {proportion.successes}/{proportion.trials} = {point}, "
        f"95% Wilson interval [{proportion.wilson_lower:.1%}, {proportion.wilson_upper:.1%}]"
    )


def _opt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _opt_pp(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}pp"


def _opt_num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"
