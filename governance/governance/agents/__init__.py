"""The four governance agents, in the order they appear in a Recommendation."""

from __future__ import annotations

from governance.agents import audit, compliance, performance, risk
from governance.agents.base import AGENT_NAMES, GovernanceAgent

# Keyed by the same names AGENT_NAMES lists, so the coordinator can order opinions
# deterministically regardless of the order LangGraph finishes the parallel nodes in.
AGENT_MODULES = {
    risk.NAME: risk,
    performance.NAME: performance,
    compliance.NAME: compliance,
    audit.NAME: audit,
}

__all__ = ["AGENT_MODULES", "AGENT_NAMES", "GovernanceAgent"]
