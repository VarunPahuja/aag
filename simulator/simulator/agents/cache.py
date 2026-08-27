"""
simulator/agents/cache.py
--------------------------
File-based decision cache for the GeminiAgent.

WHY WE NEED THIS:
  One LLM call per invoice × hundreds of invoices × repeated simulation runs
  = thousands of calls against Gemini rate limits + slow CI.
  The cache ensures that once Gemini has decided on an invoice (identified by
  content hash + prompt version), the decision is replayed instantly forever.

CACHE KEY:
  SHA-256 of JSON-serialised invoice content (excluding generated IDs and
  timestamps) + agent prompt version string.  If the prompt changes, the
  version string changes, and all old cache entries are effectively invalidated.

STORAGE:
  One JSON file per cache entry in fixtures/cache/<first-2-hex>/<hash>.json.
  Using a two-level directory prevents any single directory from having
  thousands of files (bad for file systems and ls).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from simulator.constants import AGENT_PROMPT_VERSION
from simulator.models import AgentOutcome, Invoice


class DecisionCache:
    """
    File-based cache for AgentDecisionRecord objects.

    Thread safety: NOT thread-safe by design (the simulator is single-threaded).
    """

    def __init__(
        self,
        cache_dir: str | Path,
        prompt_version: str = AGENT_PROMPT_VERSION,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.prompt_version = prompt_version
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, invoice: Invoice) -> Optional[AgentOutcome]:
        """Return a cached decision record, or None if not cached."""
        key = self._make_key(invoice)
        path = self._key_to_path(key)
        if not path.exists():
            self._misses += 1
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            record = AgentOutcome(**data)
            record.from_cache = True
            record.cache_key = key
            self._hits += 1
            return record
        except Exception:
            # Corrupted cache file — treat as miss
            self._misses += 1
            return None

    def put(self, invoice: Invoice, record: AgentOutcome) -> str:
        """Store a decision record in the cache. Returns the cache key."""
        key = self._make_key(invoice)
        path = self._key_to_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Annotate record with cache metadata before saving
        record.from_cache = False
        record.cache_key = key
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return key

    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": self._hits + self._misses,
            "hit_rate_pct": (
                round(100 * self._hits / (self._hits + self._misses))
                if (self._hits + self._misses) > 0
                else 0
            ),
        }

    def clear(self) -> int:
        """Delete all cache files. Returns number of files deleted."""
        count = 0
        for f in self.cache_dir.rglob("*.json"):
            f.unlink()
            count += 1
        return count

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def _make_key(self, invoice: Invoice) -> str:
        """
        SHA-256 of stable invoice fields + prompt version.

        We exclude: invoice_id, created_at, ground_truth_* (those are
        oracle answers, not the content the LLM sees).
        """
        stable = {
            "vendor_name": invoice.vendor_name,
            "category": invoice.category,
            "amount": invoice.amount,
            "invoice_date": str(invoice.invoice_date),
            "submitted_by": invoice.submitted_by,
            "department": invoice.department,
            "cost_centre": invoice.cost_centre,
            "purchase_order": invoice.purchase_order,
            "description": invoice.description,
            "missing_field_names": sorted(invoice.missing_field_names),
            "prompt_version": self.prompt_version,
        }
        payload = json.dumps(stable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _key_to_path(self, key: str) -> Path:
        """Two-level shard path: cache_dir/<first2>/<key>.json"""
        return self.cache_dir / key[:2] / f"{key}.json"
