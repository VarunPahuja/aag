"""The Policy Engine (docs/lanes/vp.md, ADR-0003, ADR-0014).

The only code in this system that decides whether an agent's action is
permitted. Pure functions, no database, no network, no LLM — see
`backend/tests/test_policy_import_boundary.py`, which fails the build if this
package or anything it imports pulls in a forbidden dependency.

Public surface: `evaluate_decision` (may the agent act, or must it escalate)
and `clamp_recommendation` (the hard ceiling between a governance proposal and
an agent's actual limit).
"""

from __future__ import annotations

from app.policy.ceiling import ClampResult, clamp_recommendation
from app.policy.engine import evaluate_decision
from app.policy.types import Invoice, PolicyDecision, PolicyVersion

__all__ = [
    "ClampResult",
    "Invoice",
    "PolicyDecision",
    "PolicyVersion",
    "clamp_recommendation",
    "evaluate_decision",
]
