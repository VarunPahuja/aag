"""Tests for the prompt layer: rendering, loading, and response validation.

Every test here runs offline. Nothing in `governance/prompts/` touches a network, which
is what makes the whole layer testable before the Gemini client exists at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest
from shared.contracts import AgentOpinion, TrustEvaluation
from shared.enums import OpinionVerdict
from shared.reason_codes import HUMAN_READABLE

from governance.agents import AGENT_NAMES
from governance.prompts import (
    FIELD_ORDER,
    PROMPT_VERSION,
    OpinionParseError,
    OpinionResponse,
    build_prompt,
    evidence,
    evidence_fingerprint,
    gemini_response_schema,
    load_prompt_text,
    parse_opinion,
    render_evidence,
    response_json_schema,
)
from governance.prompts.schema import MAX_CONCERN_CHARS, MAX_CONCERNS

_ALL_FIXTURES = (
    "healthy_increase",
    "thin_sample",
    "active_drift",
    "recent_critical_error",
    "blocked_by_cooldown",
    "empty_history",
)

# --- evidence rendering ---------------------------------------------------------------


def test_evidence_is_deterministic(healthy_increase):
    """Cached mode keys on this text. If it varies, every fixture misses."""
    assert render_evidence(healthy_increase) == render_evidence(healthy_increase)
    assert evidence_fingerprint(healthy_increase) == evidence_fingerprint(healthy_increase)


def test_different_evidence_gets_a_different_fingerprint(healthy_increase, thin_sample):
    assert evidence_fingerprint(healthy_increase) != evidence_fingerprint(thin_sample)


@pytest.mark.parametrize("fixture_name", _ALL_FIXTURES)
def test_every_fixture_renders_without_error(request, fixture_name):
    evaluation = request.getfixturevalue(fixture_name)
    rendered = render_evidence(evaluation)
    assert rendered.strip()
    # The renderer must not invent a value where the contract allows None.
    assert "None" not in rendered


def test_wilson_bounds_reach_the_prompt(thin_sample):
    """The lower bound is the number the whole lane reasons about."""
    rendered = render_evidence(thin_sample)
    assert "72.2%" in rendered
    assert "Wilson" in rendered


def test_reason_codes_are_described_not_just_listed(blocked_by_cooldown):
    """Each code must carry its real sentence from HUMAN_READABLE.

    Asserting the exact text matters here. `describe()` takes a *list*; handed a bare
    string it iterates the characters and emits "[C] [O] [O] [L] ..." — structurally
    valid output that tells a model nothing. A weaker assertion passed that bug.
    """
    rendered = render_evidence(blocked_by_cooldown)

    assert blocked_by_cooldown.reason_codes, "fixture must carry reason codes to be a test"
    for code in blocked_by_cooldown.reason_codes:
        assert f"- {code}: {HUMAN_READABLE[code]}" in rendered


def test_no_reason_code_renders_as_bracketed_characters(request):
    """The describe()-arity bug, pinned across every fixture."""
    for fixture_name in _ALL_FIXTURES:
        rendered = render_evidence(request.getfixturevalue(fixture_name))
        assert "[C] [O]" not in rendered
        assert not re.search(r"\[[A-Z]\] \[[A-Z]\]", rendered), fixture_name


def test_underpowered_flag_is_visible(thin_sample):
    assert "underpowered: True" in render_evidence(thin_sample)


def test_empty_history_says_no_evidence(empty_history):
    assert "no evidence (0 trials)" in render_evidence(empty_history)


# --- prompt loading -------------------------------------------------------------------


@pytest.mark.parametrize("agent_name", AGENT_NAMES)
def test_every_agent_has_a_prompt_file(agent_name):
    assert load_prompt_text(agent_name).strip()


def test_shared_preamble_exists():
    assert load_prompt_text("shared").strip()


def test_a_missing_prompt_file_raises(healthy_increase):
    with pytest.raises(FileNotFoundError, match="no prompt file"):
        load_prompt_text("nonexistent_agent")


@pytest.mark.parametrize("agent_name", AGENT_NAMES)
def test_prompt_carries_preamble_agent_brief_evidence_and_schema(agent_name, healthy_increase):
    prompt = build_prompt(agent_name, healthy_increase)

    assert prompt.agent_name == agent_name
    assert prompt.version == PROMPT_VERSION
    # System half: the shared constitution plus this agent's own brief.
    assert "You do not produce **authority**" in prompt.system
    assert load_prompt_text(agent_name)[:60] in prompt.system
    # User half: the evidence, then the output contract.
    assert render_evidence(healthy_increase) in prompt.user
    assert "Required output" in prompt.user


def test_cache_key_binds_agent_version_and_evidence(healthy_increase, thin_sample):
    """A prompt edit or an evidence change must miss the cache, not replay a stale answer."""
    risk_healthy = build_prompt("risk", healthy_increase)
    audit_healthy = build_prompt("audit", healthy_increase)
    risk_thin = build_prompt("risk", thin_sample)

    assert risk_healthy.cache_key != audit_healthy.cache_key
    assert risk_healthy.cache_key != risk_thin.cache_key
    assert risk_healthy.cache_key.startswith(f"risk.{PROMPT_VERSION}.")


def test_no_prompt_invites_the_model_to_set_a_limit(healthy_increase):
    """The schema has nowhere to write authority; the text must not imply otherwise."""
    schema_properties = set(response_json_schema()["properties"])
    assert schema_properties == {"verdict", "reasoning", "concerns", "confidence"}

    for agent_name in AGENT_NAMES:
        prompt = build_prompt(agent_name, healthy_increase)
        assert "proposed_limit" not in prompt.system
        assert "You cannot change a limit" in prompt.system


# --- prompt injection boundary --------------------------------------------------------


# Every string-typed field of TrustEvaluation the renderer is permitted to interpolate.
# All three are system-generated: agent_id is minted by the backend, reason codes are a
# closed vocabulary in shared/reason_codes.py, and component names are set by the trust
# engine. Nothing here originates with a supplier.
APPROVED_FREE_TEXT_FIELDS = frozenset({"agent_id", "reason_codes"})


def test_no_free_text_from_invoices_reaches_the_prompt():
    """Pin *which* string-typed fields the renderer reads, not what its output says.

    Invoice text is supplier-controlled. Rendering any of it would let a supplier write
    instructions into a memo field and argue their own agent into a higher limit
    (see evidence.py's module docstring).

    Asserting on field names rather than on output text is the point. A test that
    scanned the rendered string for "ignore previous instructions" would pass happily on
    the day someone adds a vendor-supplied description field — which is precisely the
    regression worth catching.
    """
    source = (Path(evidence.__file__)).read_text(encoding="utf-8")
    referenced = set(re.findall(r"evaluation\.([a-z_]+)", source))

    string_typed = {
        field.name
        for field in fields(TrustEvaluation)
        if "str" in str(field.type) and field.name != "schema_version"
    }

    leaked = (referenced & string_typed) - APPROVED_FREE_TEXT_FIELDS
    assert not leaked, (
        f"evidence.py interpolates string-typed field(s) {sorted(leaked)} into an LLM "
        f"prompt. If these can carry supplier-controlled text, that is indirect prompt "
        f"injection — see evidence.py's module docstring. Widening this needs an ADR."
    )


def test_the_approved_fields_still_exist_on_the_contract():
    """Guards the guard: a renamed field in shared/ must not silently empty the allowlist."""
    contract_fields = {field.name for field in fields(TrustEvaluation)}
    assert APPROVED_FREE_TEXT_FIELDS <= contract_fields


# --- the Gemini dialect ---------------------------------------------------------------


def test_gemini_schema_has_no_refs_or_defs():
    """Gemini's responseSchema is an OpenAPI 3.0 subset with no $ref resolution.

    Pydantic hoists the OpinionVerdict enum into $defs and references it; sent as-is,
    the API rejects it. This is the integration failure worth catching offline rather
    than at the first live call.
    """
    schema = gemini_response_schema()
    serialised = json.dumps(schema)

    assert "$defs" not in serialised
    assert "$ref" not in serialised
    assert "additionalProperties" not in serialised


def test_gemini_schema_inlines_the_verdict_enum():
    verdict = gemini_response_schema()["properties"]["verdict"]
    assert verdict["type"] == "string"
    assert set(verdict["enum"]) == {"CONCUR", "OBJECT", "ABSTAIN"}


def test_gemini_schema_resolves_nested_array_items():
    concerns = gemini_response_schema()["properties"]["concerns"]
    assert concerns["type"] == "array"
    assert concerns["items"]["type"] == "string"


def test_reasoning_is_ordered_before_verdict():
    """The model must argue before it concludes, not rationalise afterwards."""
    ordering = gemini_response_schema()["propertyOrdering"]
    assert ordering.index("reasoning") < ordering.index("verdict")
    assert ordering.index("concerns") < ordering.index("verdict")


def test_field_order_matches_the_model_exactly():
    """A field added to OpinionResponse without an ordering entry would be ordered
    arbitrarily by the API, silently undoing the reasoning-first property."""
    assert tuple(OpinionResponse.model_fields) == FIELD_ORDER
    assert set(gemini_response_schema()["properties"]) == set(FIELD_ORDER)


def test_gemini_schema_still_offers_no_way_to_ask_for_authority():
    """The constrained-decoding path must be as narrow as the validation path."""
    assert set(gemini_response_schema()["properties"]) == {
        "reasoning",
        "concerns",
        "verdict",
        "confidence",
    }


def test_required_fields_survive_the_translation():
    required = set(gemini_response_schema()["required"])
    assert {"reasoning", "verdict", "confidence"} <= required


# --- response validation --------------------------------------------------------------


def _payload(**overrides) -> str:
    body = {
        "verdict": "OBJECT",
        "reasoning": "The Wilson lower bound is 72.2% over 10 decisions.",
        "concerns": ["wide confidence interval"],
        "confidence": 0.7,
    }
    body.update(overrides)
    return json.dumps(body)


def test_a_well_formed_response_becomes_an_opinion():
    opinion = parse_opinion(_payload(), "performance")
    assert opinion.agent_name == "performance"
    assert opinion.verdict is OpinionVerdict.OBJECT
    assert opinion.concerns == ("wide confidence interval",)
    assert opinion.confidence == 0.7


def test_lowercase_verdict_is_accepted():
    assert parse_opinion(_payload(verdict="concur"), "risk").verdict is OpinionVerdict.CONCUR


def test_fenced_json_is_accepted():
    raw = f"```json\n{_payload()}\n```"
    assert parse_opinion(raw, "risk").verdict is OpinionVerdict.OBJECT


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "I think the agent is doing well.",
        '{"verdict": "OBJECT", "reasoning": "x"',
        "[1, 2, 3]",
        '"a bare string"',
    ],
    ids=["empty", "blank", "prose", "truncated", "array", "bare-string"],
)
def test_malformed_responses_raise_rather_than_half_parse(raw):
    with pytest.raises(OpinionParseError):
        parse_opinion(raw, "risk")


@pytest.mark.parametrize(
    "overrides",
    [
        {"verdict": "APPROVE"},
        {"confidence": 7.0},
        {"confidence": -0.1},
        {"reasoning": ""},
        {"concerns": ["x"] * (MAX_CONCERNS + 1)},
        {"concerns": ["x" * (MAX_CONCERN_CHARS + 1)]},
    ],
    ids=["invented-verdict", "confidence-high", "confidence-low", "empty-reasoning",
         "too-many-concerns", "concern-too-long"],
)
def test_out_of_contract_values_are_rejected(overrides):
    with pytest.raises(OpinionParseError):
        parse_opinion(_payload(**overrides), "risk")


def test_extra_fields_are_rejected():
    """A model cannot smuggle in authority by inventing a field."""
    with pytest.raises(OpinionParseError):
        parse_opinion(_payload(proposed_limit=10000), "risk")


def test_parse_error_keeps_the_raw_text():
    """A malformed response has to be inspectable; that is the whole debugging trail."""
    with pytest.raises(OpinionParseError) as caught:
        parse_opinion("not json at all", "audit")
    assert caught.value.raw == "not json at all"


def test_empty_concerns_are_allowed():
    opinion = parse_opinion(_payload(concerns=[], verdict="CONCUR"), "compliance")
    assert opinion.concerns == ()


def test_blank_concerns_are_dropped_not_kept():
    opinion = parse_opinion(_payload(concerns=["  ", "real concern"]), "audit")
    assert opinion.concerns == ("real concern",)


def test_a_parsed_opinion_is_the_shared_frozen_contract():
    """Past parse_opinion it is a frozen dataclass — Pydantic does not leak downstream."""
    opinion = parse_opinion(_payload(), "risk")

    assert isinstance(opinion, AgentOpinion)
    assert replace(opinion, agent_name="audit").agent_name == "audit"
    with pytest.raises(FrozenInstanceError):
        opinion.agent_name = "audit"  # type: ignore[misc]
