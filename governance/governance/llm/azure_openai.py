"""The Azure OpenAI client — chat only, via the Responses API.

Raw HTTP, the same choice `gemini.py` makes and for the same first two reasons: the
request shape stays visible in a dict a reader can point at, and `httpx` is already a
hard dependency (via langgraph) so this needs no optional extra the way `openai_client.py`
does.

**Not the classic Azure OpenAI surface.** `AZURE_OPENAI_ENDPOINT` here is the *full*
request URL for a `services.ai.azure.com` resource's Responses API
(`.../openai/v1/responses`), used verbatim — not the bare resource root the `openai`
SDK's `AzureOpenAI(azure_endpoint=...)` builder expects, and not the
`chat/completions?api-version=...` shape `openai_client.py` sends. Probed against a real
deployment on 14 Sept 2026: this surface takes `api-key` as a header and rejects an
`api-version` query parameter outright ("API version not supported") — GA versionless,
unlike the dated `api-version` the classic endpoint still requires. `AZURE_OPENAI_API_VERSION`
is read and kept on the config for whoever's resource does need it, but nothing here
sends it; add it back at the call site if a different resource's endpoint demands one.

**This is a paid provider, deliberately, and that is a decision made in this change —
not an oversight.** `assistant/embed.py` and `docs/lanes/vc.md` are explicit that no
paid service should quietly become part of the default path, and ADR-0012 (swappable
providers) is still Proposed rather than settling which paid providers are in scope.
Azure OpenAI is wired in here anyway, on the team lead's explicit instruction, scoped to
*chat* (`backend/app/services/assistant_llm.py`'s answer-generation step) — never the
default (`DEFAULT_PROVIDER` in `registry.py` stays Gemini) and never the embedding path
(`assistant/embed.py` still raises `EmbeddingsUnsupportedError` for anything but Gemini;
`gpt-4.1-mini` is a chat model and could not produce those vectors regardless). ADR-0012
should be updated to say so explicitly rather than leaving this client as the thing that
settles it by accident.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

from governance.llm.base import DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT_S, Pacer, model_slug
from governance.llm.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
)
from governance.prompts.loader import Prompt
from governance.prompts.schema import strict_json_schema

PROVIDER = "azure-openai"

# The deployment actually provisioned for this project's Azure AI Foundry resource. A
# fallback, not a promise: any other deployment name works, set via
# AZURE_OPENAI_DEPLOYMENT.
DEFAULT_DEPLOYMENT = "gpt-4.1-mini"

SCHEMA_NAME = "agent_opinion"

# Conservative and, unlike Gemini's MODEL_RPM, not read off a dashboard — an Azure
# resource's real rate limit is set per-deployment in the Azure portal and nobody has
# checked it for this one. Same floor `OpenAIConfig` picks for the classic endpoint.
DEFAULT_MIN_INTERVAL_S = 1.0


@dataclass(frozen=True, slots=True)
class AzureOpenAIConfig:
    """Everything the client needs, resolved once.

    An empty `api_key` is not an error at construction time, matching every other
    provider here: stub and cached modes must run with the variable unset.
    """

    api_key: str = ""
    endpoint: str = ""
    deployment: str = DEFAULT_DEPLOYMENT
    api_version: str = ""
    temperature: float = DEFAULT_TEMPERATURE
    timeout_s: float = DEFAULT_TIMEOUT_S
    min_interval_s: float = DEFAULT_MIN_INTERVAL_S

    @classmethod
    def from_env(cls, **overrides: object) -> AzureOpenAIConfig:
        base: dict[str, object] = {
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY", "").strip(),
            "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip(),
            "deployment": (
                os.environ.get("AZURE_OPENAI_DEPLOYMENT", DEFAULT_DEPLOYMENT).strip()
                or DEFAULT_DEPLOYMENT
            ),
            "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "").strip(),
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)


@dataclass
class AzureOpenAIClient:
    """One client, one deployment, one pacer."""

    config: AzureOpenAIConfig = field(default_factory=AzureOpenAIConfig.from_env)
    provider: str = PROVIDER
    _pacer: Pacer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._pacer = Pacer(self.config.min_interval_s)

    @property
    def model(self) -> str:
        """The deployment name — what this endpoint actually treats as `model`."""
        return self.config.deployment

    @property
    def has_key(self) -> bool:
        return self.config.has_key

    @property
    def slug(self) -> str:
        return model_slug(self.provider, self.config.deployment)

    def build_request(self, prompt: Prompt) -> dict:
        """Constrained to the `AgentOpinion` schema, Responses-API dialect.

        `instructions` + `input` are the Responses API's system/user split — not
        `messages`, which is the older chat-completions shape `openai_client.py` sends.
        """
        return {
            "model": self.config.deployment,
            "instructions": prompt.system,
            "input": prompt.user,
            "temperature": self.config.temperature,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": SCHEMA_NAME,
                    "schema": strict_json_schema(),
                    "strict": True,
                }
            },
        }

    def build_request_text(self, prompt: Prompt) -> dict:
        """Same request as `build_request`, minus the structured-output constraint."""
        return {
            "model": self.config.deployment,
            "instructions": prompt.system,
            "input": prompt.user,
            "temperature": self.config.temperature,
        }

    def generate(
        self,
        prompt: Prompt,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        return self._send(self.build_request(prompt), client=client, timeout_s=timeout_s)

    def generate_text(
        self,
        prompt: Prompt,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        return self._send(self.build_request_text(prompt), client=client, timeout_s=timeout_s)

    def _send(
        self,
        body: dict,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        if not self.config.api_key:
            raise LLMAuthError(
                "AZURE_OPENAI_API_KEY is empty. Azure OpenAI is an optional provider — "
                "set GOVERNANCE_PROVIDER=gemini (or GOVERNANCE_PROVIDER_ASSISTANT=gemini) "
                "to use the free tier instead, or put a key in .env (which is gitignored)."
            )
        if not self.config.endpoint:
            raise LLMAuthError(
                "AZURE_OPENAI_ENDPOINT is empty. It is the full Responses API URL from "
                "the Azure AI Foundry portal (…/openai/v1/responses), not just the "
                "resource root — put it in .env."
            )
        if not self.config.deployment:
            raise LLMAuthError("AZURE_OPENAI_DEPLOYMENT is empty. Put it in .env.")

        self._pacer.wait()
        headers = {"api-key": self.config.api_key, "content-type": "application/json"}
        deadline = self.config.timeout_s if timeout_s is None else timeout_s

        owns_client = client is None
        http = client or httpx.Client(timeout=deadline)
        try:
            response = http.post(self.config.endpoint, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMTransportError(
                f"Azure OpenAI call timed out after {deadline}s: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMTransportError(f"Azure OpenAI call failed to complete: {exc}") from exc
        finally:
            if owns_client:
                http.close()

        _raise_for_status(response)
        return _extract_text(response)


def _raise_for_status(response: httpx.Response) -> None:
    status = response.status_code
    if status < 400:
        return

    detail = _error_message(response)

    if status == 429:
        raise LLMRateLimitError(
            f"Azure OpenAI rate limit hit (429): {detail}.",
            retry_after=_retry_after(response),
        )
    if status in (401, 403):
        raise LLMAuthError(
            f"Azure OpenAI rejected the API key ({status}): {detail}. Check "
            f"AZURE_OPENAI_API_KEY in .env and that the resource, deployment and key "
            f"all belong to the same Azure AI Foundry project."
        )
    if status >= 500:
        raise LLMTransportError(f"Azure OpenAI server error ({status}): {detail}")
    raise LLMResponseError(f"Azure OpenAI rejected the request ({status}): {detail}")


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300].strip() or "<empty body>"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return str(payload)[:300]


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_text(response: httpx.Response) -> str:
    """Dig the text out of the Responses API's `output` envelope.

    `output` is a list of items — reasoning items, tool calls, and (what this client
    asks for) exactly one `message` item whose own `content` list holds the answer as
    an `output_text` block. A refusal replaces that block with a `refusal` one at either
    level and is HTTP 200, so it is checked before falling through to "no usable text",
    the same distinction `claude.py` draws for a stop_reason of `refusal`.
    """
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMResponseError(f"Azure OpenAI returned a non-JSON body: {exc}") from exc

    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "refusal":
            raise LLMResponseError(
                f"Azure OpenAI refused the request: {item.get('refusal') or '<no reason given>'}"
            )
        if item.get("type") != "message":
            continue
        parts: list[str] = []
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "refusal":
                raise LLMResponseError(
                    f"Azure OpenAI refused the request: "
                    f"{block.get('refusal') or '<no reason given>'}"
                )
            if block.get("type") == "output_text":
                parts.append(block.get("text", ""))
        text = "".join(parts).strip()
        if text:
            return text

    status = payload.get("status")
    reason = (payload.get("incomplete_details") or {}).get("reason")
    raise LLMResponseError(
        f"Azure OpenAI returned no usable output text (status={status!r}, "
        f"incomplete_reason={reason!r})."
    )
