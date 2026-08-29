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

# Reasoning first, verdict after it. See OpinionResponse's docstring — a model fills
# fields in order, so this decides whether it argues its way to a conclusion or
# rationalises one it already committed to.
FIELD_ORDER: tuple[str, ...] = ("reasoning", "concerns", "verdict", "confidence")

# Keys Gemini's OpenAPI 3.0 subset understands. Anything Pydantic emits outside this
# set is dropped by _to_openapi_subset rather than sent and silently ignored.
_SUPPORTED_KEYS = frozenset(
    {"type", "enum", "description", "format", "nullable", "minimum", "maximum"}
)

# Claude and OpenAI take strict JSON Schema, which is a wider dialect than Gemini's —
# it keeps the length and range constraints Gemini's subset has nowhere to put.
_STRICT_KEYS = frozenset(
    {
        "type",
        "enum",
        "description",
        "format",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
    }
)


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

    **Field order is deliberate: reasoning first, verdict after.** A model fills a
    structured response in field order, so each field it writes conditions the next. A
    schema that asks for `verdict` first makes the model commit to CONCUR or OBJECT
    before it has written a word of analysis, leaving the reasoning field to
    rationalise a conclusion already reached. Asking for the argument first and the
    verdict second is the same reason you would not ask a reviewer for their decision
    before their review. `FIELD_ORDER` carries this to the API as `propertyOrdering`.
    """

    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    # Descriptions are part of the contract, not commentary: they travel into the
    # Gemini schema and are the only thing telling a model what `confidence` measures.
    # Without one, models read it as "how trustworthy is the agent" — the wrong
    # quantity, and wrong in a way that looks entirely plausible in the output.
    reasoning: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_REASONING_CHARS,
            description=(
                "Your argument, citing the specific numbers you relied on. Write this "
                "before deciding your verdict."
            ),
        ),
    ]
    concerns: Annotated[
        list[str],
        Field(
            max_length=MAX_CONCERNS,
            description=(
                "Short, specific flags a human reviewer should see. May be empty. "
                "Do not invent a concern in order to appear useful."
            ),
        ),
    ] = []
    verdict: Annotated[
        OpinionVerdict,
        Field(
            description=(
                "CONCUR if the evidence supports the proposed direction, OBJECT if it "
                "does not and you can say why, ABSTAIN if this proposal does not engage "
                "your specialism or there is too little evidence to judge."
            ),
        ),
    ]
    confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description=(
                "How confident you are in your own verdict — not how trustworthy the "
                "agent under review is. Low confidence with a clear verdict is coherent."
            ),
        ),
    ]

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


def gemini_response_schema() -> dict:
    """The same contract, in the dialect the Gemini API accepts.

    Gemini's `responseSchema` is a *subset of OpenAPI 3.0*, not full JSON Schema, and
    Pydantic emits several things that subset does not contain:

    - `$defs` / `$ref` — Pydantic hoists the `OpinionVerdict` enum into a definition and
      references it. Gemini has no `$ref` resolution, so the enum has to be inlined.
    - `additionalProperties` — the mechanism behind `extra="forbid"`. Not in the subset.
    - `title`, `default` — accepted or ignored depending on endpoint; dropped here so the
      payload contains only what is actually specified.

    Passing this as `response_schema` with `response_mime_type="application/json"` gives
    constrained decoding: malformed JSON becomes structurally impossible rather than
    merely discouraged.

    **This does not make `parse_opinion()` redundant.** Constrained decoding guarantees
    the *shape* of a response, never its *sense* — `confidence: 0.99` beside two words of
    reasoning satisfies every constraint here. Validation stays.
    """
    source = OpinionResponse.model_json_schema()
    defs = source.get("$defs", {})

    properties = {
        name: _to_openapi_subset(spec, defs) for name, spec in source["properties"].items()
    }

    return {
        "type": "object",
        "properties": properties,
        "required": list(source.get("required", [])),
        # Reasoning before verdict. See the OpinionResponse docstring — this is the
        # whole point of declaring an order rather than letting the API pick one.
        "propertyOrdering": list(FIELD_ORDER),
    }


def strict_json_schema() -> dict:
    """The same contract in the strict-JSON-Schema dialect Claude and OpenAI both take.

    Anthropic wants it under `output_config={"format": {"type": "json_schema", ...}}`;
    OpenAI wants it under `response_format={"type": "json_schema", ...}` with
    `strict: true`. Both impose the same two rules, and both differ from Gemini:

    - **`additionalProperties: false` is required**, not forbidden. It is the mechanism
      behind `extra="forbid"`, and Gemini's OpenAPI subset has no place to put it.
    - **Every property must appear in `required`.** Pydantic omits `concerns` because it
      has a default, but a strict schema has no notion of an optional field — so the
      model is asked for all four and returns an empty list when it has no concerns.
      That is the same contract `OpinionResponse` already validates, stated differently.

    `$defs` are inlined here too. Neither provider resolves a `$ref` pointing at a
    definitions block that constrained decoding never receives.
    """
    source = OpinionResponse.model_json_schema()
    defs = source.get("$defs", {})

    properties = {
        name: _to_strict_subset(spec, defs) for name, spec in source["properties"].items()
    }
    return {
        "type": "object",
        "properties": properties,
        # Every field, not source["required"] — see the docstring.
        "required": list(FIELD_ORDER),
        "additionalProperties": False,
    }


def _to_strict_subset(spec: dict, defs: dict) -> dict:
    """Inline `$ref`s and drop the Pydantic bookkeeping neither provider reads."""
    if "$ref" in spec:
        ref_name = spec["$ref"].rsplit("/", 1)[-1]
        if ref_name not in defs:
            raise KeyError(f"cannot inline unknown schema reference {spec['$ref']!r}")
        spec = {**defs[ref_name], **{k: v for k, v in spec.items() if k != "$ref"}}

    resolved = {
        key: value
        for key, value in spec.items()
        if key in _STRICT_KEYS
    }
    if "items" in spec:
        resolved["items"] = _to_strict_subset(spec["items"], defs)
    return resolved


def _to_openapi_subset(spec: dict, defs: dict) -> dict:
    """Resolve one property spec into Gemini's dialect.

    Recursive because `concerns` is an array whose `items` needs the same treatment;
    `$ref` inlining is one level deep in practice, but resolving generically means a
    future nested model does not silently emit a `$ref` Gemini will reject at runtime.
    """
    if "$ref" in spec:
        ref_name = spec["$ref"].rsplit("/", 1)[-1]
        if ref_name not in defs:
            raise KeyError(f"cannot inline unknown schema reference {spec['$ref']!r}")
        spec = defs[ref_name]

    resolved = {key: value for key, value in spec.items() if key in _SUPPORTED_KEYS}

    if "items" in spec:
        resolved["items"] = _to_openapi_subset(spec["items"], defs)

    return resolved
