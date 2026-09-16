"""Tests for the Azure OpenAI client (the assistant chat path only — see module
docstring in `governance/llm/azure_openai.py` for why this provider has no
`AgentOpinion`-schema request builder).

No test here touches the network — the SDK client is exercised through an injected
stub, same style as `test_providers.py`'s OpenAI coverage, since Azure's v1 surface is
called through the same `openai` package.
"""

from __future__ import annotations

import pytest

from governance.llm.azure_openai import (
    AzureOpenAIClient,
    AzureOpenAIConfig,
    _resource_root,
)
from governance.llm.base import model_slug
from governance.llm.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
)
from governance.prompts.loader import Prompt


def _prompt() -> Prompt:
    return Prompt(
        agent_name="assistant-general",
        version="v2",
        system="You help with this page.",
        user="How do I approve this invoice?",
        evidence_hash="abc123",
    )


def _stub_openai(response=None, raises: type[Exception] | None = None):
    class _Completions:
        def create(self, **kwargs):
            if raises is not None:
                raise raises("upstream said so")
            return response

    chat = type("_Chat", (), {"completions": _Completions()})()
    return type("_Sdk", (), {"chat": chat})()


# --------------------------------------------------------------- endpoint normalisation


def test_a_full_request_url_is_reduced_to_the_resource_root():
    """This project's own `.env` carries the full endpoint URL, not a resource root."""
    assert (
        _resource_root("https://varunpahuja-resource.services.ai.azure.com/openai/v1/responses")
        == "https://varunpahuja-resource.services.ai.azure.com"
    )


def test_a_bare_resource_root_passes_through_unchanged():
    assert (
        _resource_root("https://varunpahuja-resource.services.ai.azure.com")
        == "https://varunpahuja-resource.services.ai.azure.com"
    )


def test_a_trailing_slash_does_not_change_the_root():
    assert (
        _resource_root("https://varunpahuja-resource.services.ai.azure.com/")
        == "https://varunpahuja-resource.services.ai.azure.com"
    )


def test_base_url_appends_the_v1_path():
    config = AzureOpenAIConfig(
        api_key="k", endpoint="https://x.services.ai.azure.com/openai/v1/responses"
    )
    assert config.base_url == "https://x.services.ai.azure.com/openai/v1/"


# --------------------------------------------------------------- config


def test_config_from_env_tolerates_everything_blank(monkeypatch):
    for var in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"):
        monkeypatch.delenv(var, raising=False)
    config = AzureOpenAIConfig.from_env()
    assert config.api_key == ""
    assert config.has_key is False
    assert config.deployment  # falls back to DEFAULT_DEPLOYMENT, never empty


def test_config_reads_from_the_environment(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "  from-env  ")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.services.ai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    config = AzureOpenAIConfig.from_env()
    assert config.api_key == "from-env"
    assert config.deployment == "gpt-4.1-mini"


# --------------------------------------------------------------- slug


def test_model_slug_prefixes_the_provider():
    assert model_slug("azure-openai", "gpt-4.1-mini") == "azure-openai-gpt-4-1-mini"


# --------------------------------------------------------------- request shape


def test_request_carries_system_and_user_as_plain_messages():
    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    request = client.build_request_text(_prompt())
    assert request["model"] == "gpt-4.1-mini"
    assert request["messages"] == [
        {"role": "system", "content": "You help with this page."},
        {"role": "user", "content": "How do I approve this invoice?"},
    ]
    assert "response_format" not in request  # free text, not the AgentOpinion schema


# --------------------------------------------------------------- key/endpoint checks


def test_a_missing_key_names_the_variable():
    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    with pytest.raises(LLMAuthError, match="AZURE_OPENAI_API_KEY"):
        client.generate_text(_prompt(), client=_stub_openai())


def test_a_missing_endpoint_names_the_variable():
    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="", deployment="gpt-4.1-mini")
    )
    with pytest.raises(LLMAuthError, match="AZURE_OPENAI_ENDPOINT"):
        client.generate_text(_prompt(), client=_stub_openai())


def test_generate_is_not_implemented_for_the_governance_panel_schema():
    """This provider only serves the assistant's free-text path. A misconfigured
    GOVERNANCE_PROVIDER*=azure-openai on the panel must fail loudly, not degrade to
    prose that then fails to parse as an AgentOpinion two calls later."""
    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    with pytest.raises(NotImplementedError, match="assistant"):
        client.generate(_prompt())


# --------------------------------------------------------------- happy path / errors


def test_a_successful_call_returns_the_model_text():
    choice = type(
        "_C", (), {"finish_reason": "stop", "message": type("_M", (), {"content": "Click Approve."})()}
    )()
    response = type("_R", (), {"choices": [choice]})()

    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    text = client.generate_text(_prompt(), client=_stub_openai(response))
    assert text == "Click Approve."


def test_errors_map_onto_the_shared_hierarchy():
    stub_error = type("RateLimitError", (Exception,), {})
    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    with pytest.raises(LLMRateLimitError) as caught:
        client.generate_text(_prompt(), client=_stub_openai(raises=stub_error))
    assert caught.value.retryable is True


def test_a_truncated_response_blames_max_tokens():
    choice = type("_C", (), {"finish_reason": "length", "message": None})()
    response = type("_R", (), {"choices": [choice]})()

    client = AzureOpenAIClient(
        config=AzureOpenAIConfig(api_key="k", endpoint="https://x", deployment="gpt-4.1-mini")
    )
    with pytest.raises(LLMResponseError, match="max_tokens"):
        client.generate_text(_prompt(), client=_stub_openai(response))
