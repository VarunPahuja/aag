"""What every provider client has to be, and the pacing they all share.

**Why more than one provider.** The strongest objection to this lane is that four
agents on the same base model are not four independent reviewers — they share a base
model, so they share its biases, and their errors correlate. The structural answer
(governance is advisory, so correlated error degrades the argument rather than the
safety) is true but defensive. Running the panel across genuinely different base models
is the actual mitigation: a Gemini risk agent and a Claude performance agent do not fail
the same way.

**Nothing here is required to run the project.** Gemini has a free tier and stays the
default; `anthropic` and `openai` are optional extras, and the whole system still runs
end to end with every key blank (docs/lanes/vc.md forbids introducing a paid service).
See ADR-0012.

A client's whole job is: take a `Prompt`, return the model's raw text. It does not
validate, parse, or build an `AgentOpinion` — that stays behind `parse_opinion()`, so
adding a provider cannot accidentally add a second validation path.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Protocol, runtime_checkable

from governance.prompts.loader import Prompt

# Free-tier Gemini is roughly ten requests per minute, and it is the tightest limit of
# the three, so it sets the shared default. Each provider may raise it.
DEFAULT_MIN_INTERVAL_S = 6.0
DEFAULT_TIMEOUT_S = 30.0

# Governance opinions should be reproducible enough that a recording is representative.
# Not zero: at temperature 0 a reasoning task tends to produce the same terse argument
# every time, and the panel's value comes from four agents actually differing.
DEFAULT_TEMPERATURE = 0.2

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def model_slug(provider: str, model: str) -> str:
    """A filesystem-safe identity for one provider/model pair.

    Model ids carry dots (`gemini-2.5-flash`) and the recording cache key is
    dot-delimited, so dots have to go or the key stops being parseable by eye.

    The provider is prefixed only when the model id does not already carry it —
    `gemini-2.5-flash` becomes `gemini-2-5-flash`, not `gemini-gemini-2-5-flash`, while
    OpenAI's `gpt-4o` becomes `openai-gpt-4o` because nothing in the id says who made it.
    """
    provider = provider.lower()
    slug = _SLUG_STRIP.sub("-", model.lower()).strip("-")
    if slug.startswith(f"{provider}-") or slug == provider:
        return slug
    return f"{provider}-{slug}"


@runtime_checkable
class LLMClient(Protocol):
    """One provider, one model. Prompt in, raw text out."""

    provider: str
    model: str

    def generate(self, prompt: Prompt) -> str: ...

    @property
    def has_key(self) -> bool: ...

    @property
    def slug(self) -> str: ...


class Pacer:
    """Spaces requests by at least `min_interval` seconds.

    Deliberately a floor on the gap between calls rather than a token bucket. A bucket
    permits a burst, and a burst is exactly what a free tier punishes: the first four
    agents would go out instantly and the fifth would be rate-limited. Thread-safe
    because a parallel recording run would otherwise pace nothing at all.
    """

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call: float | None = None

    def wait(self) -> float:
        """Block until the next call is allowed. Returns the seconds actually slept."""
        with self._lock:
            now = time.monotonic()
            if self._last_call is None:
                self._last_call = now
                return 0.0
            delay = max(0.0, self._min_interval - (now - self._last_call))
            if delay > 0:
                time.sleep(delay)
            self._last_call = time.monotonic()
            return delay
