"""Versioned prompts, evidence rendering, and validated structured output.

The 30 Aug deliverable's first half (docs/DEADLINES.md). What is here: prompt files per
agent, a deterministic evidence renderer, and a Pydantic boundary that every model
response has to pass before the rest of the lane sees it.

What is deliberately not here yet: any code that calls Gemini. Cached replay and the
live client land next; keeping the prompt layer free of a client means it can be tested
in full without a network, and `stub` mode never imports an SDK it does not use.
"""

from __future__ import annotations

from governance.prompts.evidence import evidence_fingerprint, render_evidence
from governance.prompts.loader import (
    PROMPT_VERSION,
    Prompt,
    build_prompt,
    load_prompt_text,
)
from governance.prompts.schema import (
    FIELD_ORDER,
    OpinionParseError,
    OpinionResponse,
    gemini_response_schema,
    parse_opinion,
    response_json_schema,
)

__all__ = [
    "FIELD_ORDER",
    "PROMPT_VERSION",
    "OpinionParseError",
    "OpinionResponse",
    "Prompt",
    "build_prompt",
    "evidence_fingerprint",
    "gemini_response_schema",
    "load_prompt_text",
    "parse_opinion",
    "render_evidence",
    "response_json_schema",
]
