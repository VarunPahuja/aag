"""Shared enums. TREATY FILE — changes require all four reviewers.

Every lane imports these. Do not redefine any of them locally, and do not add a lane-
specific value here.
"""

from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    """What the agent did, or what ground truth says it should have done.

    ESCALATE is only ever an *agent* action. Ground truth is always APPROVE or REJECT,
    because every synthetic invoice carries a deterministic correct answer.
    """

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


class AgentState(str, Enum):
    PROBATION = "probation"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"


class DriftSeverity(str, Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    CONFIRMED = "CONFIRMED"
    CRITICAL = "CRITICAL"


class Direction(str, Enum):
    INCREASE = "INCREASE"
    HOLD = "HOLD"
    CLAWBACK = "CLAWBACK"