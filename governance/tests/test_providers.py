"""Provider selection, the three request dialects, and the keying bug they exposed.

No test here touches the network, and none requires `anthropic` or `openai` to be
installed — the SDK clients are exercised through injected stubs, and exception mapping
is matched on class name rather than on imported types. That is deliberate: the optional
extras must stay optional, including in CI (ADR-0012).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import make_evaluation

from governance.agents.base import AGENT_NAMES
from governance.agents.llm_backed import opine_via_model
from governance.llm.base import LLMClient, model_slug
from governance.llm.claude import ClaudeClient, ClaudeConfig
from governance.llm.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    RecordingMissError,
)
from governance.llm.openai_client import OpenAIClient, OpenAIConfig
from governance.llm.recording import RecordingStore, build_recording, cache_key_for
from governance.llm.registry import (
    DEFAULT_PROVIDER,
    PROVIDERS,
    UnknownProviderError,
    build_client,
    describe_panel,
    reset_clients,
    resolve_provider,
)
from governance.modes import CACHED
from governance.prompts.loader import build_prompt

VALID_RESPONSE = json.dumps(
    {
        "reasoning": "196 of 200 decisions correct, Wilson lower bound 95.0%.",
        "concerns": [],
        "verdict": "CONCUR",
        "confidence": 0.82,
    }
)

GEMINI_SLUG = "gemini-2-5-flash"
CLAUDE_SLUG = "claude-opus-5"


def _recording_for(prompt, slug: str = GEMINI_SLUG, provider: str = "gemini"):
    return build_recording(
        prompt, VALID_RESPONSE, f"{provider}-model", provider=provider, model_slug=slug
    )


def _stub_anthropic(response=None, raises: type[Exception] | None = None):
    """A stand-in for `anthropic.Anthropic` with just the surface the client touches."""

    class _Messages:
        def create(self, **kwargs):
            if raises is not None:
                raise raises("upstream said so")
            return response

    return type("_Sdk", (), {"messages": _Messages()})()


def _stub_openai(response=None, raises: type[Exception] | None = None):
    class _Completions:
        def create(self, **kwargs):
            if raises is not None:
                raise raises("upstream said so")
            return response

    chat = type("_Chat", (), {"completions": _Completions()})()
    return type("_Sdk", (), {"chat": chat})()


def _blocks(*pairs):
    return [type("_B", (), {"type": t, "text": x})() for t, x in pairs]


# --------------------------------------------------------------- selection


def test_the_three_providers_are_registered():
    assert PROVIDERS == ("gemini", "claude", "openai")
    assert DEFAULT_PROVIDER == "gemini"


def test_gemini_is_the_default_because_it_is_the_only_free_tier(monkeypatch):
    """docs/lanes/vc.md forbids introducing a paid service, so the default cannot be one."""
    monkeypatch.delenv("GOVERNANCE_PROVIDER", raising=False)
    assert resolve_provider() == "gemini"


def test_a_per_agent_override_beats_the_global_setting(monkeypatch):
    """The whole point of the feature: four agents on one base model share its biases,
    so their errors correlate and the panel is less independent than it looks."""
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "gemini")
    monkeypatch.setenv("GOVERNANCE_PROVIDER_RISK", "claude")

    panel = describe_panel(AGENT_NAMES)
    assert panel["risk"] == "claude"
    assert panel["performance"] == "gemini"
    assert len(set(panel.values())) == 2


def test_an_unknown_provider_raises_rather_than_silently_using_the_default(monkeypatch):
    """A typo'd provider that quietly ran on Gemini would look like a working
    mixed-model panel while being nothing of the sort."""
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "claud")
    with pytest.raises(UnknownProviderError, match="claud"):
        resolve_provider()


def test_the_error_names_the_variable_it_came_from(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_PROVIDER_AUDIT", "gemmini")
    with pytest.raises(UnknownProviderError, match="GOVERNANCE_PROVIDER_AUDIT"):
        resolve_provider("audit")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_every_client_satisfies_the_protocol_without_a_key(monkeypatch, provider):
    """Constructing a client must never need a key — stub and cached modes have to run
    end to end with every variable blank."""
    for var in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    reset_clients()

    client = build_client(provider=provider)
    assert isinstance(client, LLMClient)
    assert client.provider == provider
    assert client.has_key is False
    assert client.slug


# --------------------------------------------------------------- slugs


def test_model_slug_does_not_repeat_the_provider_name():
    assert model_slug("gemini", "gemini-2.5-flash") == "gemini-2-5-flash"
    assert model_slug("claude", "claude-opus-5") == "claude-opus-5"
    assert model_slug("openai", "gpt-4o") == "openai-gpt-4o"


def test_model_slug_strips_characters_that_would_break_a_key_or_a_path():
    """Keys are dot-delimited and become filenames; a dot or slash breaks both."""
    slug = model_slug("openai", "gpt-4.1/preview")
    assert "." not in slug
    assert "/" not in slug


# --------------------------------------------------------------- the keying bug


def test_two_providers_do_not_collide_on_one_recording(tmp_path: Path):
    """The bug this release fixes. Keyed without the model, a panel switched from
    Gemini to Claude replays Gemini's recordings and looks perfectly healthy: same
    agent, same evidence, plausible reasoning, wrong model."""
    evaluation = make_evaluation()
    prompt = build_prompt("risk", evaluation)
    store = RecordingStore(directory=tmp_path)

    store.save(_recording_for(prompt, slug=GEMINI_SLUG))

    assert store.has(cache_key_for(prompt, GEMINI_SLUG))
    assert not store.has(cache_key_for(prompt, CLAUDE_SLUG))

    with pytest.raises(RecordingMissError):
        opine_via_model("risk", evaluation, CACHED, store=store, model_slug=CLAUDE_SLUG)


def test_the_cache_key_carries_agent_version_model_and_evidence():
    prompt = build_prompt("risk", make_evaluation())
    agent, version, slug, evidence = cache_key_for(prompt, CLAUDE_SLUG).split(".")
    assert (agent, version, slug) == ("risk", "v1", CLAUDE_SLUG)
    assert evidence == prompt.evidence_hash


def test_a_recording_records_which_provider_produced_it(tmp_path: Path):
    """Provenance: without it, a replayed opinion cannot say which model argued it."""
    store = RecordingStore(directory=tmp_path)
    prompt = build_prompt("risk", make_evaluation())
    store.save(_recording_for(prompt, slug=CLAUDE_SLUG, provider="claude"))

    loaded = store.load(cache_key_for(prompt, CLAUDE_SLUG))
    assert loaded.provider == "claude"


def test_a_mixed_panel_replays_each_agent_from_its_own_provider(tmp_path: Path):
    """The end state the feature exists for: risk on Claude, the rest on Gemini,
    every opinion coming from the model that actually produced it."""
    evaluation = make_evaluation()
    store = RecordingStore(directory=tmp_path)

    store.save(_recording_for(build_prompt("risk", evaluation), CLAUDE_SLUG, "claude"))
    for name in ("performance", "compliance", "audit"):
        store.save(_recording_for(build_prompt(name, evaluation), GEMINI_SLUG, "gemini"))

    slugs = {"risk": CLAUDE_SLUG}
    for name in AGENT_NAMES:
        opinion = opine_via_model(
            name, evaluation, CACHED, store=store, model_slug=slugs.get(name, GEMINI_SLUG)
        )
        assert opinion.agent_name == name


# --------------------------------------------------------------- request dialects


def test_claude_gets_strict_json_schema_not_geminis_dialect():
    """Claude and OpenAI need `additionalProperties: false` and every field required;
    Gemini's OpenAPI subset has nowhere to put either. Sending the wrong dialect fails
    at the API, which is a slow way to find out."""
    prompt = build_prompt("risk", make_evaluation())
    request = ClaudeClient(config=ClaudeConfig(api_key="k")).build_request(prompt)

    schema = request["output_config"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert sorted(schema["required"]) == ["concerns", "confidence", "reasoning", "verdict"]
    assert "$ref" not in json.dumps(schema)


def test_claude_is_not_sent_a_temperature():
    """Sampling parameters were removed on Claude Opus 5 and return a 400."""
    prompt = build_prompt("risk", make_evaluation())
    request = ClaudeClient(config=ClaudeConfig(api_key="k")).build_request(prompt)
    assert "temperature" not in request


def test_openai_asks_for_strict_mode():
    prompt = build_prompt("risk", make_evaluation())
    request = OpenAIClient(config=OpenAIConfig(api_key="k")).build_request(prompt)

    schema_block = request["response_format"]["json_schema"]
    assert schema_block["strict"] is True
    assert schema_block["schema"]["additionalProperties"] is False


def test_every_provider_puts_the_system_prompt_somewhere_sane():
    prompt = build_prompt("risk", make_evaluation())

    claude = ClaudeClient(config=ClaudeConfig(api_key="k")).build_request(prompt)
    assert claude["system"] == prompt.system

    openai = OpenAIClient(config=OpenAIConfig(api_key="k")).build_request(prompt)
    assert openai["messages"][0] == {"role": "system", "content": prompt.system}


@pytest.mark.parametrize(
    ("factory", "env_var"),
    [
        (lambda: ClaudeClient(config=ClaudeConfig(api_key="")), "ANTHROPIC_API_KEY"),
        (lambda: OpenAIClient(config=OpenAIConfig(api_key="")), "OPENAI_API_KEY"),
    ],
)
def test_an_optional_provider_without_a_key_names_its_variable(factory, env_var):
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMAuthError, match=env_var):
        factory().generate(prompt)


# --------------------------------------------------------------- error mapping


@pytest.mark.parametrize(
    ("raised", "expected", "retryable"),
    [
        ("RateLimitError", LLMRateLimitError, True),
        ("AuthenticationError", LLMAuthError, False),
        ("PermissionDeniedError", LLMAuthError, False),
        ("APIConnectionError", LLMTransportError, True),
        ("APITimeoutError", LLMTransportError, True),
        ("BadRequestError", LLMResponseError, False),
    ],
)
def test_sdk_exceptions_map_onto_the_shared_hierarchy(raised, expected, retryable):
    """Live mode's fallback rule reads `retryable`, so the flag is the contract — and
    matching by class name is what lets this run without the SDKs installed."""
    stub_error = type(raised, (Exception,), {})
    prompt = build_prompt("risk", make_evaluation())

    with pytest.raises(expected) as caught:
        ClaudeClient(config=ClaudeConfig(api_key="k")).generate(
            prompt, client=_stub_anthropic(raises=stub_error)
        )
    assert caught.value.retryable is retryable
    assert "upstream said so" in str(caught.value)


def test_openai_errors_map_the_same_way():
    stub_error = type("RateLimitError", (Exception,), {})
    prompt = build_prompt("risk", make_evaluation())

    with pytest.raises(LLMRateLimitError) as caught:
        OpenAIClient(config=OpenAIConfig(api_key="k")).generate(
            prompt, client=_stub_openai(raises=stub_error)
        )
    assert caught.value.retryable is True


# --------------------------------------------------------------- response reading


def test_claude_text_is_read_past_a_thinking_block():
    """Thinking is on by default on Opus 5, so content[0] is not always the answer."""
    response = type(
        "_R",
        (),
        {
            "stop_reason": "end_turn",
            "content": _blocks(("thinking", "ignore me"), ("text", VALID_RESPONSE)),
        },
    )()

    prompt = build_prompt("risk", make_evaluation())
    text = ClaudeClient(config=ClaudeConfig(api_key="k")).generate(
        prompt, client=_stub_anthropic(response)
    )
    assert json.loads(text)["verdict"] == "CONCUR"


def test_a_claude_refusal_says_it_was_refused():
    """A refusal is HTTP 200. Without this check it would surface as an empty-response
    parse failure with nothing explaining why."""
    response = type(
        "_R",
        (),
        {
            "stop_reason": "refusal",
            "stop_details": type("_D", (), {"category": "cyber"})(),
            "content": [],
        },
    )()

    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="refusal"):
        ClaudeClient(config=ClaudeConfig(api_key="k")).generate(
            prompt, client=_stub_anthropic(response)
        )


def test_a_truncated_openai_response_blames_max_tokens_not_the_parser():
    """Truncated JSON would otherwise fail in parse_opinion() with a message that never
    mentions the real cause."""
    choice = type("_C", (), {"finish_reason": "length", "message": None})()
    response = type("_R", (), {"choices": [choice]})()

    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="max_tokens"):
        OpenAIClient(config=OpenAIConfig(api_key="k")).generate(
            prompt, client=_stub_openai(response)
        )


def test_an_openai_content_filter_is_distinguished_from_an_empty_answer():
    choice = type("_C", (), {"finish_reason": "content_filter", "message": None})()
    response = type("_R", (), {"choices": [choice]})()

    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="content_filter"):
        OpenAIClient(config=OpenAIConfig(api_key="k")).generate(
            prompt, client=_stub_openai(response)
        )


def test_agents_on_one_provider_share_a_client_and_therefore_a_pacer(monkeypatch):
    """A rate limit belongs to the key, not the agent. Two Gemini agents with a pacer
    each would send at twice the free tier's rate and 429 on the recording run."""
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "gemini")
    monkeypatch.delenv("GOVERNANCE_PROVIDER_RISK", raising=False)
    monkeypatch.delenv("GOVERNANCE_PROVIDER_AUDIT", raising=False)
    reset_clients()

    assert build_client("risk") is build_client("audit")


def test_agents_on_different_providers_do_not_share_a_client(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "gemini")
    monkeypatch.setenv("GOVERNANCE_PROVIDER_RISK", "claude")
    reset_clients()

    assert build_client("risk") is not build_client("audit")
