"""The Azure OpenAI client, via the official `openai` SDK's v1 (OpenAI-compatible) API.

Optional, on the same terms as Claude and OpenAI — Gemini's free tier stays the default
and the project runs end to end with every key blank (docs/lanes/vc.md, ADR-0012). The
import is lazy so a missing package is an actionable error rather than an ImportError at
load.

**Why not `openai.AzureOpenAI`.** That class speaks the older `api-version`-query-param
dialect. Azure resources created against the newer unified surface (an "AI Foundry"
resource, in this project's case) also accept the same `/openai/v1/` path the plain
OpenAI SDK talks to everywhere else — no `api-version`, `deployment` doubling as
`model`. Verified directly against this project's own resource: `client.responses.create`,
`client.chat.completions.create` with `base_url=f"{resource_root}/openai/v1/"`, and the
classic `AzureOpenAI(azure_endpoint=..., api_version=...)` all answered. Chat Completions
via the v1 base_url was chosen because it lets this client reuse the exact request/response
shape `openai_client.py` already uses — one request builder, one response reader, one
error translator, for the two providers that happen to speak the same dialect.

**The endpoint is normalised, not trusted verbatim.** `AZURE_OPENAI_ENDPOINT` in this
project's `.env` carries a full request URL
(`https://…/openai/v1/responses`), not a resource root, because that's what was pasted
in from the Azure portal. Rather than requiring an exact shape, `_resource_root` strips
everything from `/openai/` onward, so either a bare resource root or a full endpoint URL
in that variable produces the same base_url.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from governance.llm.base import (
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_S,
    Pacer,
    model_slug,
)
from governance.llm.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
    ProviderUnavailableError,
)
from governance.prompts.loader import Prompt

PROVIDER = "azure-openai"

DEFAULT_DEPLOYMENT = "gpt-4.1-mini"
DEFAULT_MAX_TOKENS = 2048


def _resource_root(endpoint: str) -> str:
    """`https://x.services.ai.azure.com/openai/v1/responses` -> `https://x.services.ai.azure.com`.

    A bare resource root (no `/openai/` suffix at all) passes through unchanged.
    """
    endpoint = endpoint.strip().rstrip("/")
    if "/openai/" in endpoint:
        endpoint = endpoint.split("/openai/", 1)[0]
    return endpoint


@dataclass(frozen=True, slots=True)
class AzureOpenAIConfig:
    api_key: str = ""
    endpoint: str = ""
    deployment: str = DEFAULT_DEPLOYMENT
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout_s: float = DEFAULT_TIMEOUT_S
    min_interval_s: float = 1.0

    @classmethod
    def from_env(cls, **overrides: object) -> AzureOpenAIConfig:
        base: dict[str, object] = {
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY", "").strip(),
            "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip(),
            "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT", DEFAULT_DEPLOYMENT).strip()
            or DEFAULT_DEPLOYMENT,
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    @property
    def base_url(self) -> str:
        return f"{_resource_root(self.endpoint)}/openai/v1/"


@dataclass
class AzureOpenAIClient:
    """One Azure OpenAI deployment, one pacer. See module docstring for the API shape."""

    config: AzureOpenAIConfig = field(default_factory=AzureOpenAIConfig.from_env)
    provider: str = PROVIDER
    _pacer: Pacer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._pacer = Pacer(self.config.min_interval_s)

    @property
    def model(self) -> str:
        return self.config.deployment

    @property
    def has_key(self) -> bool:
        return self.config.has_key

    @property
    def slug(self) -> str:
        return model_slug(self.provider, self.config.deployment)

    def build_request_text(self, prompt: Prompt) -> dict:
        """Prose, not the `AgentOpinion` schema — this client only serves
        `generate_text()`, the assistant's chat path. There is no `generate()`/
        `build_request()` pair here because nothing asks this provider for a
        governance panel opinion (see `docs/ASSISTANT-INTEGRATION.md`)."""
        return {
            "model": self.config.deployment,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
        }

    def generate(
        self,
        prompt: Prompt,
        *,
        client: object | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """Not implemented: this client has no `AgentOpinion`-schema request builder,
        because nothing asks it for one (only the assistant's `generate_text()` uses
        this provider — see `docs/ASSISTANT-INTEGRATION.md`). Raising here, rather than
        silently degrading to `generate_text()`'s free-text prose, means a
        `GOVERNANCE_PROVIDER*=azure-openai` misconfiguration on the panel fails loudly
        with a message that names the fix, instead of confusingly at
        `parse_opinion()` two calls later."""
        raise NotImplementedError(
            "AzureOpenAIClient.generate() is not implemented — this provider only "
            "serves the assistant chat path (generate_text()), not the governance "
            "panel's structured AgentOpinion output. Use GOVERNANCE_PROVIDER_ASSISTANT "
            "for the assistant, and gemini/claude/openai for GOVERNANCE_PROVIDER*."
        )

    def generate_text(
        self,
        prompt: Prompt,
        *,
        client: object | None = None,
        timeout_s: float | None = None,
    ) -> str:
        return self._send(self.build_request_text(prompt), client=client, timeout_s=timeout_s)

    def _send(
        self,
        request: dict,
        *,
        client: object | None = None,
        timeout_s: float | None = None,
    ) -> str:
        if not self.config.has_key:
            raise LLMAuthError(
                "AZURE_OPENAI_API_KEY is empty. Set it, AZURE_OPENAI_ENDPOINT and "
                "AZURE_OPENAI_DEPLOYMENT in .env (which is gitignored), or point "
                "GOVERNANCE_PROVIDER_ASSISTANT at gemini/claude/openai instead."
            )
        if not self.config.endpoint:
            raise LLMAuthError(
                "AZURE_OPENAI_ENDPOINT is empty. It needs the resource's base URL "
                "(e.g. https://<resource>.services.ai.azure.com), a full request URL "
                "under it also works."
            )

        sdk = client if client is not None else self._build_client()
        self._pacer.wait()

        request = dict(request)
        if timeout_s is not None:
            request["timeout"] = timeout_s

        try:
            response = sdk.chat.completions.create(**request)
        except Exception as exc:
            raise _translate(exc) from exc

        return _extract_text(response)

    def _build_client(self) -> object:
        try:
            import openai
        except ImportError as exc:
            raise ProviderUnavailableError(
                "the 'openai' package is not installed. It is an optional extra: "
                "pip install 'governance[openai]'. Gemini needs no extra."
            ) from exc
        return openai.OpenAI(
            base_url=self.config.base_url, api_key=self.config.api_key, timeout=self.config.timeout_s
        )


def _translate(exc: Exception) -> Exception:
    """Map an SDK exception onto this lane's hierarchy. Same SDK as `openai_client.py`
    (Azure's v1 surface is called through the plain `openai` package), so the same
    exception class names apply — only the message points at the Azure variables."""
    name = type(exc).__name__
    message = str(exc)

    if name == "RateLimitError":
        return LLMRateLimitError(f"Azure OpenAI rate limit hit: {message}")
    if name in ("AuthenticationError", "PermissionDeniedError"):
        return LLMAuthError(
            f"Azure OpenAI rejected the request: {message}. Check AZURE_OPENAI_API_KEY, "
            f"AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT in .env."
        )
    if name in ("APITimeoutError", "APIConnectionError", "InternalServerError"):
        return LLMTransportError(f"Azure OpenAI call failed to complete: {message}")
    if name == "BadRequestError":
        return LLMResponseError(
            f"Azure OpenAI rejected the request: {message}. Check that "
            f"AZURE_OPENAI_DEPLOYMENT names a deployment that actually exists on this "
            f"resource."
        )
    if name == "NotFoundError":
        return LLMResponseError(
            f"Azure OpenAI returned 404: {message}. Check AZURE_OPENAI_ENDPOINT and "
            f"AZURE_OPENAI_DEPLOYMENT — the deployment name has to match the resource "
            f"exactly."
        )
    if name.endswith("Error") and name.startswith("API"):
        return LLMTransportError(f"Azure OpenAI call failed: {message}")
    return exc


def _extract_text(response: object) -> str:
    """Pull the message content out of the first choice. Mirrors
    `openai_client._extract_text` — same response envelope, same failure modes."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise LLMResponseError("Azure OpenAI returned no choices.")

    choice = choices[0]
    finish = getattr(choice, "finish_reason", None)
    if finish == "length":
        raise LLMResponseError(
            f"Azure OpenAI truncated the response at max_tokens={DEFAULT_MAX_TOKENS}."
        )
    if finish == "content_filter":
        raise LLMResponseError(
            "Azure OpenAI filtered the response rather than answering it "
            "(finish_reason='content_filter')."
        )

    text = (getattr(getattr(choice, "message", None), "content", None) or "").strip()
    if not text:
        raise LLMResponseError(f"Azure OpenAI returned an empty message (finish_reason={finish!r}).")
    return text
