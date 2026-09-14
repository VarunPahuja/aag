"""The Azure OpenAI client — request shape, the Responses API's `output` envelope, and
error mapping. Same `httpx.MockTransport` pattern `test_llm.py` uses for Gemini, since
this client is also raw HTTP rather than an SDK wrapper.

The exact shapes asserted on here (headers, `output`/`content`/`output_text`, the
`api-version query rejected` behaviour) were confirmed against a real Azure AI Foundry
deployment on 14 Sept 2026 — see `azure_openai.py`'s docstring.
"""

from __future__ import annotations

import httpx
import pytest
from conftest import make_evaluation

from governance.llm.azure_openai import AzureOpenAIClient, AzureOpenAIConfig
from governance.llm.errors import (
    GovernanceLLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
)
from governance.prompts.loader import build_prompt


def _config(**overrides) -> AzureOpenAIConfig:
    """A config that never paces, so tests do not sleep."""
    base = {
        "api_key": "test-key",
        "endpoint": "https://example-resource.services.ai.azure.com/openai/v1/responses",
        "deployment": "gpt-4.1-mini",
        "min_interval_s": 0.0,
    }
    base.update(overrides)
    return AzureOpenAIConfig(**base)


def _client_returning(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _ok_envelope(text: str = "pong") -> dict:
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


# --------------------------------------------------------------- request shape


def test_the_request_uses_instructions_and_input_not_messages():
    """The Responses API dialect, not chat-completions' `messages` list."""
    prompt = build_prompt("risk", make_evaluation())
    body = AzureOpenAIClient(config=_config()).build_request(prompt)

    assert body["model"] == "gpt-4.1-mini"
    assert body["instructions"] == prompt.system
    assert body["input"] == prompt.user
    assert "messages" not in body


def test_the_request_carries_the_strict_json_schema_dialect():
    prompt = build_prompt("risk", make_evaluation())
    body = AzureOpenAIClient(config=_config()).build_request(prompt)

    schema_block = body["text"]["format"]
    assert schema_block["type"] == "json_schema"
    assert schema_block["strict"] is True
    assert schema_block["schema"]["additionalProperties"] is False
    assert "verdict" in schema_block["schema"]["properties"]


def test_generate_text_skips_the_structured_output_constraint():
    prompt = build_prompt("risk", make_evaluation())
    body = AzureOpenAIClient(config=_config()).build_request_text(prompt)
    assert "text" not in body


def test_the_key_travels_as_an_api_key_header_never_in_the_url():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("api-key")
        return httpx.Response(200, json=_ok_envelope())

    prompt = build_prompt("risk", make_evaluation())
    AzureOpenAIClient(config=_config(api_key="secret-value")).generate_text(
        prompt, client=_client_returning(handler)
    )

    assert seen["key"] == "secret-value"
    assert "secret-value" not in seen["url"]


def test_no_api_version_query_parameter_is_sent():
    """The v1 Responses API rejects `api-version` outright ('API version not
    supported') — unlike the classic Azure OpenAI endpoint. See the module docstring."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, json=_ok_envelope())

    prompt = build_prompt("risk", make_evaluation())
    AzureOpenAIClient(config=_config(api_version="2024-10-21")).generate_text(
        prompt, client=_client_returning(handler)
    )
    assert seen["query"] == {}


# --------------------------------------------------------------- happy path


def test_a_successful_call_returns_the_model_text():
    prompt = build_prompt("risk", make_evaluation())
    text = AzureOpenAIClient(config=_config()).generate_text(
        prompt, client=_client_returning(lambda _: httpx.Response(200, json=_ok_envelope()))
    )
    assert text == "pong"


def test_multiple_output_text_blocks_are_joined():
    envelope = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "{\"a\":"},
                    {"type": "output_text", "text": "1}"},
                ],
            }
        ],
    }
    prompt = build_prompt("risk", make_evaluation())
    text = AzureOpenAIClient(config=_config()).generate_text(
        prompt, client=_client_returning(lambda _: httpx.Response(200, json=envelope))
    )
    assert text == '{"a":1}'


def test_a_non_message_output_item_is_skipped_in_favour_of_the_message():
    """A reasoning item can precede the message item in `output`; only the message
    carries the answer."""
    envelope = {
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": "pong"}]},
        ],
    }
    prompt = build_prompt("risk", make_evaluation())
    text = AzureOpenAIClient(config=_config()).generate_text(
        prompt, client=_client_returning(lambda _: httpx.Response(200, json=envelope))
    )
    assert text == "pong"


# --------------------------------------------------------------- error mapping


@pytest.mark.parametrize(
    ("missing_field", "match"),
    [
        ("api_key", "AZURE_OPENAI_API_KEY"),
        ("endpoint", "AZURE_OPENAI_ENDPOINT"),
        ("deployment", "AZURE_OPENAI_DEPLOYMENT"),
    ],
)
def test_missing_config_fails_before_any_request_is_made(missing_field, match):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be sent with missing config")

    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMAuthError, match=match):
        AzureOpenAIClient(config=_config(**{missing_field: ""})).generate_text(
            prompt, client=_client_returning(handler)
        )


@pytest.mark.parametrize(
    ("status", "expected", "retryable"),
    [
        (429, LLMRateLimitError, True),
        (401, LLMAuthError, False),
        (403, LLMAuthError, False),
        (500, LLMTransportError, True),
        (503, LLMTransportError, True),
        (404, LLMResponseError, False),
        (400, LLMResponseError, False),
    ],
)
def test_http_status_maps_to_the_right_error_and_retryability(status, expected, retryable):
    """404 is included deliberately: a bad AZURE_OPENAI_DEPLOYMENT name returns 404
    'DeploymentNotFound' on this API, confirmed live — not a 400."""
    body = {"error": {"message": "upstream said so"}}
    prompt = build_prompt("risk", make_evaluation())

    with pytest.raises(expected) as caught:
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(lambda _: httpx.Response(status, json=body))
        )

    assert caught.value.retryable is retryable
    assert "upstream said so" in str(caught.value)


def test_a_rate_limit_carries_retry_after_when_the_server_sends_one():
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMRateLimitError) as caught:
        AzureOpenAIClient(config=_config()).generate_text(
            prompt,
            client=_client_returning(
                lambda _: httpx.Response(429, json={}, headers={"retry-after": "21"})
            ),
        )
    assert caught.value.retry_after == 21.0


def test_a_timeout_is_a_retryable_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMTransportError) as caught:
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(handler)
        )
    assert caught.value.retryable is True


def test_a_top_level_refusal_says_it_was_refused_rather_than_empty():
    envelope = {"status": "completed", "output": [{"type": "refusal", "refusal": "policy"}]}
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="policy"):
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(lambda _: httpx.Response(200, json=envelope))
        )


def test_a_content_level_refusal_says_it_was_refused_rather_than_empty():
    envelope = {
        "status": "completed",
        "output": [
            {"type": "message", "content": [{"type": "refusal", "refusal": "content policy"}]}
        ],
    }
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="content policy"):
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(lambda _: httpx.Response(200, json=envelope))
        )


def test_no_message_item_names_the_status_rather_than_failing_opaquely():
    envelope = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(LLMResponseError, match="max_output_tokens"):
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(lambda _: httpx.Response(200, json=envelope))
        )


def test_every_client_error_is_a_governance_llm_error():
    prompt = build_prompt("risk", make_evaluation())
    with pytest.raises(GovernanceLLMError):
        AzureOpenAIClient(config=_config()).generate_text(
            prompt, client=_client_returning(lambda _: httpx.Response(500, json={}))
        )


# --------------------------------------------------------------- config


def test_config_from_env_tolerates_missing_values(monkeypatch):
    """Stub and cached modes must work with every AZURE_OPENAI_* variable unset."""
    for var in (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    ):
        monkeypatch.delenv(var, raising=False)

    config = AzureOpenAIConfig.from_env()
    assert config.has_key is False
    assert config.deployment == "gpt-4.1-mini"  # the documented fallback


def test_config_reads_every_value_from_the_environment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.services.ai.azure.com/openai/v1/responses")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "custom-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    config = AzureOpenAIConfig.from_env()
    assert config.api_key == "env-key"
    assert config.endpoint == "https://x.services.ai.azure.com/openai/v1/responses"
    assert config.deployment == "custom-deployment"
    assert config.api_version == "2025-01-01-preview"


def test_model_and_slug_are_derived_from_the_deployment_name():
    client = AzureOpenAIClient(config=_config(deployment="gpt-4.1-mini"))
    assert client.model == "gpt-4.1-mini"
    assert client.slug == "azure-openai-gpt-4-1-mini"
