"""
simulator/agents/scripted.py
-----------------------------
ScriptedAgent — implements AgentProtocol with configurable error injection.

PURPOSE (two scenarios):
  1. "We can govern any agent, including third-party ones."
     The ScriptedAgent pretends to be a third-party black-box agent.
     It follows a simple deterministic rule set (approve/reject/escalate by
     amount thresholds) but injects a controlled fraction of wrong decisions.
     The governance layer treats it identically to the LLM agent.

  2. Fast offline testing without any LLM calls or API keys.
     Before you have a Gemini key, you can run the full simulation pipeline
     end-to-end with the ScriptedAgent to verify the runner, cache, API client,
     and fixture generation all work.

IMPORTANT:
  The ScriptedAgent's mistakes are SCRIPTED (deliberate, not genuine).
  This is different from the GeminiAgent whose mistakes are REAL.
  For the demo, the drift detector should be run against LLM agent data.
  The ScriptedAgent is a governance test bed, not the primary demo subject.
"""

from __future__ import annotations

import random
import sys
import os
from decimal import Decimal

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from shared.constants import CATEGORY_LIMIT_OVERRIDES, DEFAULT_SEED
from shared.contracts import AgentDecisionRecord, Invoice
from shared.enums import AgentDecision, AutonomyTier, InvoiceCategory
from shared import reason_codes as RC


class ScriptedAgent:
    """
    A deterministic rule-following agent with a configurable error rate.

    Args:
        agent_id:    Stable identifier (used by runner and cache namespace)
        name:        Display name
        error_rate:  Fraction of decisions that will be wrong (0.0 – 1.0)
        seed:        Random seed for the error injection (reproducible)
        tier:        Autonomy tier to use for limit lookups
    """

    def __init__(
        self,
        agent_id: str = "scripted-agent-001",
        name: str = "ScriptedAgent v1",
        error_rate: float = 0.08,
        seed: int = DEFAULT_SEED,
        tier: AutonomyTier = AutonomyTier.LOW,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.error_rate = error_rate
        self.tier = tier
        self._rng = random.Random(seed)

    def decide(self, invoice: Invoice) -> AgentDecisionRecord:
        """Decide on an invoice using simple rules + optional error injection."""
        correct_decision, correct_reason = self._rule_based_decision(invoice)

        if self._rng.random() < self.error_rate:
            # Inject a wrong decision (opposite of correct)
            wrong_decision, wrong_reason = self._flip_decision(
                correct_decision, invoice
            )
            return AgentDecisionRecord(
                invoice_id=invoice.invoice_id,
                agent_id=self.agent_id,
                decision=wrong_decision,
                reason=wrong_reason,
                confidence=0.6,   # Lower confidence signals uncertainty
                from_cache=False,
            )

        return AgentDecisionRecord(
            invoice_id=invoice.invoice_id,
            agent_id=self.agent_id,
            decision=correct_decision,
            reason=correct_reason,
            confidence=0.9,
            from_cache=False,
        )

    # ------------------------------------------------------------------
    # Internal decision logic
    # ------------------------------------------------------------------

    def _rule_based_decision(
        self, invoice: Invoice
    ) -> tuple[AgentDecision, str]:
        """Simple rules — similar to labeller but less sophisticated."""
        if invoice.missing_field_names:
            return AgentDecision.ESCALATE, RC.ESCALATE_MISSING_FIELDS

        amount = Decimal(invoice.amount)
        if amount <= 0:
            return AgentDecision.REJECT, RC.REJECT_NEGATIVE_AMOUNT

        try:
            cat = InvoiceCategory(invoice.category)
        except ValueError:
            return AgentDecision.REJECT, RC.REJECT_INVALID_CATEGORY

        limit = self._get_limit(cat)
        high_limit = self._get_high_limit(cat)

        if amount > high_limit:
            return AgentDecision.REJECT, RC.REJECT_EXCEEDS_LIMIT
        if amount > limit:
            return AgentDecision.ESCALATE, RC.ESCALATE_EXCEEDS_TIER

        return AgentDecision.APPROVE, RC.APPROVE_WITHIN_LIMIT

    def _flip_decision(
        self, correct: AgentDecision, invoice: Invoice
    ) -> tuple[AgentDecision, str]:
        """Return a plausible wrong decision."""
        if correct == AgentDecision.APPROVE:
            # Wrongly escalate (most common mistake)
            return AgentDecision.ESCALATE, RC.ESCALATE_BOUNDARY_AMOUNT
        if correct == AgentDecision.ESCALATE:
            # Wrongly approve (miss the escalation trigger)
            return AgentDecision.APPROVE, RC.APPROVE_WITHIN_LIMIT
        # correct == REJECT → wrongly escalate instead
        return AgentDecision.ESCALATE, RC.ESCALATE_POLICY_CONFLICT

    def _get_limit(self, category: InvoiceCategory) -> int:
        return CATEGORY_LIMIT_OVERRIDES.get(self.tier.value, {}).get(
            category.value, 5000
        )

    def _get_high_limit(self, category: InvoiceCategory) -> int:
        return CATEGORY_LIMIT_OVERRIDES.get("high", {}).get(
            category.value, 50000
        )
