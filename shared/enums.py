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


# NOTE: AgentState uses lowercase values below, unlike every other enum in this file
# (which use uppercase values matching the member name). This is a pre-existing
# inconsistency, not a new one — left as-is rather than silently changed, because the
# trust lane already compares/serialises against these exact lowercase strings and
# changing them would be a breaking change dressed up as a cosmetic one. New enums
# (RecommendationStatus, OpinionVerdict, ReviewVerdict, added in v1.1) follow the
# uppercase convention the other three enums already use.
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


class RecommendationStatus(str, Enum):
    """Lifecycle of a governance recommendation, from proposed to resolved."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class OpinionVerdict(str, Enum):
    """A single governance agent's stance on a recommendation, before opinions are
    combined into one Recommendation."""

    CONCUR = "CONCUR"
    OBJECT = "OBJECT"
    ABSTAIN = "ABSTAIN"


class ReviewVerdict(str, Enum):
    """A human reviewer's verdict on a sampled decision, from comparing the agent's
    action against what the reviewer determines was correct."""

    AGREED = "AGREED"
    DISAGREED = "DISAGREED"
    INCONCLUSIVE = "INCONCLUSIVE"