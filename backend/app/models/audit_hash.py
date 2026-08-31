"""The hash-chain helper for `audit_log` (docs/lanes/vp.md): `hash =
sha256(prev_hash + canonical_json(payload))`.

Pure functions, deliberately reusing the exact algorithm
`app/fixtures/audit.py` already hand-rolled (`_hash_entry`) — canonical JSON
means sorted keys and no whitespace, so the hash is reproducible across runs
and machines, and so a fixture built before this module existed still chains
identically through it. Ingest wiring — the code that actually appends a new
row on every mutating event — lands later; this module is the primitive that
wiring will call, tested on its own so the chain's tamper-evidence property is
verified independently of any caller.
"""

from __future__ import annotations

import hashlib
import json
from typing import Final

GENESIS_HASH: Final[str] = "0" * 64


def canonical_json(payload: dict) -> str:
    """Sorted keys, no whitespace — the one serialisation of `payload` that
    every run, on every machine, produces byte-for-byte identically."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, payload: dict) -> str:
    """`sha256(prev_hash + canonical_json(payload))`, hex-encoded."""
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()
