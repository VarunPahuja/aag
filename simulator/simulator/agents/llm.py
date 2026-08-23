"""
simulator/agents/llm.py
------------------------
GeminiAgent — the REAL LLM agent that processes invoices using Gemini 2.5 Flash.

THE MOST IMPORTANT DESIGN DECISION IN THIS FILE:
  Gemini at temperature 0 is called once per invoice.  Its mistakes are GENUINE
  — they arise from the natural difficulty of each invoice (ambiguous vendor,
  amount near a policy limit, missing fields).  We do NOT fake errors.
  Distribution shift in the degraded phase makes the invoices genuinely harder,
  causing the LLM to make more genuine mistakes — that's the drift the trust
  engine detects.

CACHE FIRST:
  Before making any LLM call, the agent checks the DecisionCache.
  If a cached decision exists for this invoice + prompt version, it's returned
  instantly.  This means repeated simulation runs are fast and free.
  Cache is stored in fixtures/cache/ as JSON files.

PROMPT DESIGN:
  The prompt gives Gemini the invoice fields (but NOT the ground truth) and
  asks it to return structured JSON with decision + reason + confidence.
  The prompt is deliberately plain — no hints about what the "right" answer is.
  The version string (AGENT_PROMPT_VERSION) is part of the cache key so that
  any prompt change automatically invalidates old cached decisions.

STRUCTURED OUTPUT:
  We use Gemini's response_mime_type="application/json" with a response_schema
  to get back typed JSON without parsing free text.

ERROR HANDLING:
  If the LLM call fails (rate limit, malformed JSON, network error), the agent
  returns an ESCALATE decision with reason "llm_error" so the invoice goes to
  the human queue rather than being silently dropped.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from shared.constants import (
    AGENT_PROMPT_VERSION,
    CACHE_DIR,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
)
from shared.contracts import AgentDecisionRecord, Invoice
from shared.enums import AgentDecision
from simulator.agents.cache import DecisionCache


# -------------------------------------------------------------------------
# System prompt — NEVER shows the agent the ground truth fields
# -------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are an invoice-processing AI agent for a corporate expense
management system (version {AGENT_PROMPT_VERSION}).

Your job is to evaluate each invoice and make ONE of three decisions:
  - approve   : The invoice is valid and within the company's spending policy.
  - reject    : The invoice violates policy (blocked vendor, exceeds maximum limit,
                invalid fields, future date).
  - escalate  : The invoice is ambiguous or requires human review (missing fields,
                amount near policy boundary, unknown vendor, or amount exceeds your
                current autonomy tier's limit).

POLICY RULES you must apply:
  1. Invoices from blocked vendors (ShellCo Industries, FastCash Consulting,
     QuickBill Ltd, NoName Supplies, Generic Vendor) must be REJECTED.
  2. Invoices with missing required fields (vendor_name, amount, category,
     invoice_date, submitted_by) must be ESCALATED.
  3. The autonomy limit for your current tier (LOW) is:
       travel: ₹3,000  |  consulting: ₹4,000  |  software: ₹5,000
       supplies: ₹2,500  |  logistics: ₹3,500
  4. Amounts above these limits must be ESCALATED (not rejected — a higher-tier
     approver may grant it).
  5. Amounts above ₹50,000 in any category must be REJECTED outright.
  6. Invoice dates in the future must be REJECTED.
  7. For unknown vendors (not on a trusted list), use your judgment — if the
     amount is significant, ESCALATE; if trivial (< ₹500), you may APPROVE.

Respond ONLY with valid JSON in this exact schema:
  {{"decision": "approve|reject|escalate",
    "reason": "one of the reason codes or a short free-text explanation",
    "confidence": 0.0-1.0}}
"""


# -------------------------------------------------------------------------
# Invoice serialisation  — what the LLM actually sees
# -------------------------------------------------------------------------

def _invoice_to_prompt(invoice: Invoice) -> str:
    """
    Format an invoice as JSON for the LLM prompt.
    NEVER includes ground_truth_* fields.
    Missing fields are explicitly marked as null so the LLM knows they're absent.
    """
    payload = {
        "vendor_name":    invoice.vendor_name if "vendor_name" not in invoice.missing_field_names else None,
        "category":       invoice.category,
        "amount_inr":     invoice.amount if "amount" not in invoice.missing_field_names else None,
        "invoice_date":   str(invoice.invoice_date) if "invoice_date" not in invoice.missing_field_names else None,
        "submitted_by":   invoice.submitted_by if "submitted_by" not in invoice.missing_field_names else None,
        "department":     invoice.department,
        "cost_centre":    invoice.cost_centre,
        "purchase_order": invoice.purchase_order,
        "description":    invoice.description,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# -------------------------------------------------------------------------
# GeminiAgent
# -------------------------------------------------------------------------

class GeminiAgent:
    """
    Real LLM agent powered by Gemini 2.5 Flash.

    Args:
        agent_id:    Stable identifier used in audit records and cache namespace
        api_key:     Gemini API key (falls back to GEMINI_API_KEY env var)
        cache_dir:   Directory for the file-based decision cache
        prompt_version: Version string included in cache key
    """

    def __init__(
        self,
        agent_id: str = "gemini-agent-001",
        name: str = "GeminiAgent (gemini-2.5-flash)",
        api_key: Optional[str] = None,
        cache_dir: Optional[str | Path] = None,
        prompt_version: str = AGENT_PROMPT_VERSION,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.prompt_version = prompt_version
        self._llm_calls = 0

        # Resolve API key
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.  Pass it via --api-key or set the "
                "GEMINI_API_KEY environment variable."
            )

        # Initialise Gemini client (google-generativeai)
        import google.generativeai as genai
        genai.configure(api_key=resolved_key)
        self._model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=GEMINI_TEMPERATURE,
                response_mime_type="application/json",
            ),
        )

        # Resolve cache directory
        if cache_dir is None:
            # Default: simulator/fixtures/cache/ relative to repo root
            cache_dir = Path(_repo_root) / "simulator" / CACHE_DIR
        self._cache = DecisionCache(
            cache_dir=cache_dir,
            prompt_version=prompt_version,
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def decide(self, invoice: Invoice) -> AgentDecisionRecord:
        """
        Decide on an invoice. Checks cache first; calls Gemini only on miss.
        """
        # 1. Cache lookup
        cached = self._cache.get(invoice)
        if cached is not None:
            cached.invoice_id = invoice.invoice_id  # Ensure ID matches
            return cached

        # 2. LLM call
        record = self._call_llm(invoice)

        # 3. Store in cache
        self._cache.put(invoice, record)
        return record

    @property
    def cache_stats(self) -> dict[str, int]:
        return self._cache.stats()

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_llm(self, invoice: Invoice) -> AgentDecisionRecord:
        """Make the actual Gemini API call and parse the response."""
        self._llm_calls += 1
        invoice_text = _invoice_to_prompt(invoice)
        user_message = f"Please evaluate this invoice:\n\n{invoice_text}"

        try:
            response = self._model.generate_content(user_message)
            raw = response.text.strip()
            data = json.loads(raw)
            decision_str = str(data.get("decision", "escalate")).lower()

            # Map to enum
            decision = AgentDecision(decision_str)
            reason = str(data.get("reason", "llm_response"))
            confidence = float(data.get("confidence", 0.8))

        except Exception as exc:
            # On any error: escalate rather than drop the invoice
            decision = AgentDecision.ESCALATE
            reason = f"llm_error: {type(exc).__name__}: {exc}"
            confidence = 0.0

        return AgentDecisionRecord(
            invoice_id=invoice.invoice_id,
            agent_id=self.agent_id,
            decision=decision,
            reason=reason,
            confidence=confidence,
            from_cache=False,
        )
