"""The three governance modes, and how one is chosen.

Every mode must produce the same *shape* of output — a fully populated
`Recommendation`. Only the source of the reasoning text differs. Designing for all
three from day one is deliberate: retrofitting caching onto a live-only
implementation is a day this project does not have (see docs/lanes/vc.md).

`cached` is the demo default, not `live`. A recorded response cannot rate-limit,
time out, or fail in front of a panel.
"""

from __future__ import annotations

import os
from typing import Final

STUB: Final[str] = "stub"
CACHED: Final[str] = "cached"
LIVE: Final[str] = "live"

VALID_MODES: Final[tuple[str, ...]] = (STUB, CACHED, LIVE)

# stub, not cached: an unset environment must never reach for a fixture directory that
# may not exist, and must never be one typo away from a live API call.
DEFAULT_MODE: Final[str] = STUB


def resolve_mode(mode: str | None = None) -> str:
    """Pick the governance mode, preferring an explicit argument over the environment.

    An unrecognised value is an error rather than a silent fallback — a typo'd
    GOVERNANCE_MODE that quietly ran in stub mode would look exactly like a working
    demo right up until someone asked why the reasoning never changed.
    """
    chosen = mode if mode is not None else os.environ.get("GOVERNANCE_MODE", DEFAULT_MODE)
    chosen = chosen.strip().lower()
    if chosen not in VALID_MODES:
        raise ValueError(f"unknown GOVERNANCE_MODE {chosen!r}; expected one of {VALID_MODES}")
    return chosen
