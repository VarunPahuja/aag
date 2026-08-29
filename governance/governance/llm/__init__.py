"""Talking to a model provider, and replaying what it said.

Five things live here and nothing else:

- `base.py` — the `LLMClient` protocol, the shared pacer, and the model-slug rule.
- `gemini.py`, `claude.py`, `openai_client.py` — one client per provider. Each builds a
  request, sends it, and hands back raw text.
- `registry.py` — which provider serves which agent, read from the environment.
- `recording.py` — the on-disk store of real responses that `cached` mode replays.
- `errors.py` — one provider-neutral exception hierarchy, so a caller can tell "the
  model is unavailable" apart from "the model said something unusable" without knowing
  which SDK raised it.

Nothing in this package validates a response or builds an `AgentOpinion`. That is
`governance/prompts/schema.py`'s job, and keeping the split means a client can be tested
without Pydantic, the parser without a network, and a fourth provider cannot bring a
second validation path with it.

Gemini is the default and the only one with a free tier; `anthropic` and `openai` are
optional extras (ADR-0012).
"""

from __future__ import annotations

from governance.llm.base import LLMClient, Pacer, model_slug
from governance.llm.claude import ClaudeClient, ClaudeConfig
from governance.llm.errors import (
    GovernanceLLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    ProviderUnavailableError,
    RecordingMissError,
)
from governance.llm.gemini import GeminiClient, GeminiConfig
from governance.llm.openai_client import OpenAIClient, OpenAIConfig
from governance.llm.recording import Recording, RecordingStore, cache_key_for
from governance.llm.registry import (
    DEFAULT_PROVIDER,
    PROVIDERS,
    UnknownProviderError,
    build_client,
    describe_panel,
    resolve_provider,
)

__all__ = [
    "DEFAULT_PROVIDER",
    "PROVIDERS",
    "ClaudeClient",
    "ClaudeConfig",
    "GeminiClient",
    "GeminiConfig",
    "GovernanceLLMError",
    "LLMAuthError",
    "LLMClient",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTransportError",
    "OpenAIClient",
    "OpenAIConfig",
    "Pacer",
    "ProviderUnavailableError",
    "Recording",
    "RecordingMissError",
    "RecordingStore",
    "UnknownProviderError",
    "build_client",
    "cache_key_for",
    "describe_panel",
    "model_slug",
    "resolve_provider",
]
