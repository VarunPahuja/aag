"""The validated boundary between an LLM's text and the rest of this lane.

Nothing downstream of this module ever sees raw model output. A response arrives as
a string, is parsed as JSON, validated against `OpinionResponse`, and only then
converted into the frozen `AgentOpinion` dataclass the coordinator works with. If any
of those steps fails, the caller gets an `OpinionParseError` and can fall back — it
never gets a half-built opinion.

Why Pydantic here and dataclasses in `shared/`: `shared/` is a cross-lane treaty and
deliberately depends on nothing but the standard library, so the trust lane can import
it without inheriting this lane's dependencies (ADR-0005). Validation is a governance
problem — this lane is the only one holding untrusted text — so the Pydantic model
lives here and stops at this file's edge.
"""

from __future__ import annotations

import json
import re
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError, field_validator
from shared.contracts import AgentOpinion
from shared.enums import OpinionVerdict

# Models are fond of wrapping JSON in ```json fences despite being asked not to. Not
# worth a failed call and a retry over.
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)

MAX_REASONING_CHARS = 1200
MAX_CONCERNS = 6
MAX_CONCERN_CHARS = 300


class OpinionParseError(ValueError):
    """Raised when a model response cannot be turned into a valid opinion.

    Carries the raw text so a failure can be logged and inspected. In live mode this
    is the trigger for falling back to cached (due 3 Sept) — a malformed response is
    an unavailable model, not a reason to guess at what it meant.
    """

    def __init__(self, message: str, raw: str) -> None:
        super().__init__(message)
        self.raw = raw


class OpinionResponse(BaseModel):
    """Exactly what an agent prompt is allowed to return.

    Kept deliberately narrow. There is no field here for a proposed limit, a rung, or
    an action, because an agent has no say in those — it argues, the coordinator
    combines, the Policy Engine enforces, a human authorizes (ADR-0001, ADR-0004). A
    model cannot ask for more authority through this schema because the schema has
    nowhere to write it.
    """

    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    verdict: OpinionVerdict
    reasoning: Annotated[str, Field(min_length=1, max_length=MAX_REASONING_CHARS)]
    concerns: Annotated[list[str], Field(max_length=MAX_CONCERNS)] = []
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]

    @field_validator("verdict", mode="before")
    @classmethod
    def _normalise_verdict(cls, value: object) -> object:
        """Accept `concur` for `CONCUR`.

        Case is not a meaningful disagreement, and the alternative is discarding an
        otherwise sound opinion over shift-key behaviour.
        """
        return value.upper() if isinstance(value, str) else value

    @field_validator("concerns")
    @classmethod
    def _clean_concerns(cls, value: list[str]) -> list[str]:
        cleaned = [c.strip() for c in value if c and c.strip()]
        for concern in cleaned:
            if len(concern) > MAX_CONCERN_CHARS:
                raise ValueError(f"concern exceeds {MAX_CONCERN_CHARS} characters")
        return cleaned

    def to_opinion(self, agent_name: str) -> AgentOpinion:
        """Cross into the shared contract. Past this point it is a frozen dataclass."""
        return AgentOpinion(
            agent_name=agent_name,
            verdict=self.verdict,
            reasoning=self.reasoning,
            concerns=tuple(self.concerns),
            confidence=round(self.confidence, 4),
        )


def parse_opinion(raw: str, agent_name: str) -> AgentOpinion:
    """Turn one model response into a validated `AgentOpinion`, or raise.

    Every failure mode collapses to `OpinionParseError` on purpose: the caller's
    response is the same whether the model emitted prose, truncated JSON, or a
    confidence of 7 — none of those produce a usable opinion, and distinguishing them
    at the call site would only invite a partial-recovery path that guesses.
    """
    if not raw or not raw.strip():
        raise OpinionParseError(f"{agent_name}: empty response", raw)

    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpinionParseError(f"{agent_name}: response is not valid JSON ({exc})", raw) from exc

    if not isinstance(payload, dict):
        raise OpinionParseError(
            f"{agent_name}: expected a JSON object, got {type(payload).__name__}", raw
        )

    try:
        response = OpinionResponse.model_validate(payload)
    except ValidationError as exc:
        raise OpinionParseError(f"{agent_name}: response failed validation ({exc})", raw) from exc

    return response.to_opinion(agent_name)


def response_json_schema() -> dict:
    """The schema to hand a model as its structured-output spec.

    Generated from `OpinionResponse` rather than written out in the prompt text, so the
    contract a model is asked to meet and the contract its answer is checked against
    cannot drift apart.
    """
    return OpinionResponse.model_json_schema()
