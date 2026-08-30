"""Reason codes the Policy Engine attaches to a `PolicyDecision`.

Deliberately NOT in `shared/reason_codes.py`. That file's own docstring scopes
itself to codes "attached to every evaluation" — rendered by the backend,
styled by the frontend, read by governance agents reasoning about autonomy
changes. None of its eighteen codes describe why one decision was allowed or
escalated; that is a different question, asked by a different module
(docs/lanes/vp.md, responsibility 1, "the only thing in the system that
decides whether an action is permitted" — a question the trust lane's own
evaluation never asks). `shared/` is also frozen for this branch and needs
all four lane owners to change (docs/lanes/vp.md) — adding Policy Engine
codes there is exactly the kind of change that needs that sign-off, not a
unilateral addition here. See ADR-0014.

This module follows the same shape shared/reason_codes.py does (append-only
constants plus a HUMAN_READABLE map) so promoting these into shared/ later,
if the other three owners agree, is a pure move, not a rewrite. Names are
prefixed POLICY_ so they can never collide with a shared/ code if that move
happens.

Rule: append-only, same as shared/reason_codes.py. Renaming a code silently
breaks whatever reads it.
"""

from __future__ import annotations

from typing import Final

WITHIN_LIMIT: Final = "POLICY_WITHIN_LIMIT"
LIMIT_EXCEEDED: Final = "POLICY_LIMIT_EXCEEDED"
AGENT_SUSPENDED: Final = "POLICY_AGENT_SUSPENDED"
AGENT_RESTRICTED: Final = "POLICY_AGENT_RESTRICTED"
POLICY_VERSION_MISSING: Final = "POLICY_VERSION_MISSING"
POLICY_VERSION_INVALID: Final = "POLICY_VERSION_INVALID"

HUMAN_READABLE: Final[dict[str, str]] = {
    WITHIN_LIMIT: "Amount is within the agent's current limit.",
    LIMIT_EXCEEDED: "Amount exceeds the agent's current limit; escalated to a human.",
    AGENT_SUSPENDED: "Agent is suspended; every decision escalates regardless of amount.",
    AGENT_RESTRICTED: "Agent is restricted; every decision escalates regardless of amount.",
    POLICY_VERSION_MISSING: "No policy version was supplied; failing closed to escalation.",
    POLICY_VERSION_INVALID: "The policy version failed validation; failing closed to escalation.",
}


def describe(code: str) -> str:
    """Turn one code into its human-readable sentence. Mirrors
    `shared.reason_codes.describe`'s shape for a single code rather than a list —
    a `PolicyDecision` carries exactly one reason code, never several."""
    return HUMAN_READABLE.get(code, f"[{code}]")
