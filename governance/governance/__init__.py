"""Agentic Governance lane.

`recommend()` is the entry point the backend calls. Everything else here is internal.
"""

from __future__ import annotations

from governance.coordinator import build_graph, recommend
from governance.modes import CACHED, LIVE, STUB, resolve_mode

__all__ = ["CACHED", "LIVE", "STUB", "build_graph", "recommend", "resolve_mode"]
