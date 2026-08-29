"""Talking to Gemini, and replaying what it said.

Three things live here and nothing else:

- `gemini.py` — the HTTP client. Builds a request, sends it, hands back raw text.
- `recording.py` — the on-disk store of real responses that `cached` mode replays.
- `errors.py` — one exception hierarchy, so a caller can tell "the model is
  unavailable" apart from "the model said something unusable".

Nothing in this package validates a response or builds an `AgentOpinion`. That is
`governance/prompts/schema.py`'s job, and keeping the split means the client can be
tested without Pydantic in the picture and the parser can be tested without a network.
"""

from __future__ import annotations

from governance.llm.errors import (
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiTransportError,
    GovernanceLLMError,
    RecordingMissError,
)
from governance.llm.gemini import GeminiClient, GeminiConfig
from governance.llm.recording import Recording, RecordingStore

__all__ = [
    "GeminiAuthError",
    "GeminiClient",
    "GeminiConfig",
    "GeminiRateLimitError",
    "GeminiTransportError",
    "GovernanceLLMError",
    "Recording",
    "RecordingMissError",
    "RecordingStore",
]
