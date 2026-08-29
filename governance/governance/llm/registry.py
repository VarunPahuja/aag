"""Choosing a provider, and the per-agent override that makes the panel independent.

Two environment variables:

    GOVERNANCE_PROVIDER=gemini              # the default for every agent
    GOVERNANCE_PROVIDER_RISK=claude         # override one agent

The per-agent override is the point of the whole exercise, not a convenience. Four
agents on one base model share that model's biases, so their errors correlate and the
panel is less independent than it looks. Running risk on Claude while performance runs
on Gemini makes the disagreement between them mean something: two models that fail
differently, reading the same evidence.

`GOVERNANCE_PROVIDER` alone still works and keeps every agent on one provider — which is
the right default, because it is the configuration that needs no paid key.

**No key is required to import anything here.** Clients are constructed lazily and a
missing key only fails when a live call is actually attempted, because stub and cached
modes must run with every variable blank (docs/lanes/vc.md).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import cache

from governance.llm.base import LLMClient
from governance.llm.claude import PROVIDER as CLAUDE
from governance.llm.claude import ClaudeClient
from governance.llm.errors import GovernanceLLMError
from governance.llm.gemini import PROVIDER as GEMINI
from governance.llm.gemini import GeminiClient
from governance.llm.openai_client import PROVIDER as OPENAI
from governance.llm.openai_client import OpenAIClient

# Gemini first: it is the only one with a free tier, so it is the only one that can be
# the default without introducing a paid dependency.
DEFAULT_PROVIDER = GEMINI

_BUILDERS: dict[str, Callable[[], LLMClient]] = {
    GEMINI: GeminiClient,
    CLAUDE: ClaudeClient,
    OPENAI: OpenAIClient,
}

PROVIDERS: tuple[str, ...] = tuple(_BUILDERS)


class UnknownProviderError(GovernanceLLMError):
    """A provider name was set that this lane has no client for.

    Raising rather than falling back to the default, for the same reason `resolve_mode`
    raises on a typo: a misspelled `GOVERNANCE_PROVIDER=claud` that quietly ran on Gemini
    would look exactly like a working configuration, and the mixed-model panel the
    setting exists to create would silently not exist.
    """

    retryable = False


def resolve_provider(agent_name: str | None = None, *, default: str | None = None) -> str:
    """Which provider serves this agent.

    Precedence: the per-agent variable, then the global one, then Gemini. An unknown
    name raises.
    """
    chosen = default
    if chosen is None and agent_name:
        chosen = os.environ.get(f"GOVERNANCE_PROVIDER_{agent_name.upper()}")
    if chosen is None:
        chosen = os.environ.get("GOVERNANCE_PROVIDER", DEFAULT_PROVIDER)

    chosen = chosen.strip().lower()
    if chosen not in _BUILDERS:
        source = f"GOVERNANCE_PROVIDER_{agent_name.upper()}" if agent_name else "GOVERNANCE_PROVIDER"
        raise UnknownProviderError(
            f"unknown provider {chosen!r} (from {source}); expected one of {PROVIDERS}"
        )
    return chosen


@cache
def _client_for(provider: str) -> LLMClient:
    """One client per provider per process — deliberately shared, not per agent.

    **A rate limit belongs to the key, not to the agent.** Two agents on Gemini with a
    pacer each would send at twice the rate the free tier allows and spend the recording
    run backing off from 429s they created. Sharing the client shares the pacer, so the
    provider-wide gap between calls is actually honoured.

    Cached rather than constructed per call for the same reason: a fresh client would
    bring a fresh pacer with no memory of the last request.
    """
    return _BUILDERS[provider]()


def build_client(agent_name: str | None = None, *, provider: str | None = None) -> LLMClient:
    """The client serving one agent. Never raises on a missing key."""
    return _client_for(resolve_provider(agent_name, default=provider))


def reset_clients() -> None:
    """Drop the cached clients so a changed environment is picked up.

    For tests, and for anything that edits `GOVERNANCE_PROVIDER*` after import.
    """
    _client_for.cache_clear()


def describe_panel(agent_names: tuple[str, ...]) -> dict[str, str]:
    """Which provider each agent would use, for the recording script's call plan.

    Worth printing before a recording run: a panel that is accidentally four Gemini
    agents costs nothing to fix beforehand and is invisible afterwards.
    """
    return {name: resolve_provider(name) for name in agent_names}
