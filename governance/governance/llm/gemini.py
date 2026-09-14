"""The Gemini HTTP client.

Raw HTTP against the REST endpoint rather than the `google-genai` SDK. Three reasons,
in order of how much they matter here:

1. **The request is the design.** `response_schema` plus `response_mime_type` is the
   constrained-decoding claim this lane makes; having it visible in a dict a reader can
   point at is worth more in a viva than a method call that hides it.
2. **One fewer dependency.** `httpx` is already present via langgraph.
3. **The SDK's retry and safety defaults are its own.** This lane needs to decide what
   a rate limit means, because the answer feeds live mode's fallback rule.

**The key is sent as a header, never in the URL.** Query strings end up in proxy logs,
shell history, and error messages; `x-goog-api-key` does not.

Nothing here validates a response. `generate()` returns the model's text and stops, so
this module can be tested without Pydantic and the parser without a network.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import httpx

from governance.llm.base import (
    DEFAULT_MIN_INTERVAL_S,
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
)
from governance.prompts.loader import Prompt
from governance.prompts.schema import gemini_response_schema

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

# Flash: the cheapest model that follows a response schema reliably. Free tier only
# (docs/lanes/vc.md forbids a paid API), and free-tier quotas were cut sharply in Dec
# 2025 — verify against your own key rather than trusting a published number.
#
# 3.6, not 2.5: as of 30 Aug 2026 the API answers a 2.5-flash request with a 404 reading
# "no longer available to new users". A retired default is a 404 on every call, so this
# is checked by a live probe, not by a test — nothing in CI touches the network. If this
# 404s again, run one call by hand before a recording run and read the model the error
# names; the retirement notice is the only place that number is published.
DEFAULT_MODEL = "gemini-3.6-flash"

PROVIDER = "gemini"

# Requests per minute per model, read off the AI Studio rate-limit dashboard for this
# project on 2 Sept 2026 (aistudio.google.com/rate-limit — Google no longer publishes
# free-tier limits in the docs, so the dashboard is the only source, and it is per
# *project*, not per key).
#
# These differ by a factor of three between models on the same free tier, which is why
# pacing cannot be one shared constant. The Flash models allow 5 RPM; a 6s floor permits
# 10, so the previous shared default was silently twice the real limit and only survived
# because gemini-3.6-flash is slow enough (9.9-33.3s per call) that no run ever reached
# its own floor. A faster model would have turned that into 429s.
#
# RPD is the limit that actually binds a recording run and is not encoded here — the
# pacer cannot smooth a daily cap. It is recorded alongside for whoever plans the next
# run: Flash models 20/day, Flash-Lite models 500/day.
MODEL_RPM: dict[str, int] = {
    "gemini-3.7-flash": 5,  # 20 RPD
    "gemini-3.6-flash": 5,  # 20 RPD
    "gemini-3.5-flash": 5,  # 20 RPD
    "gemini-3-flash": 5,  # 20 RPD
    "gemini-2.5-flash": 5,  # 20 RPD — listed, but 404s for keys created recently
    "gemini-3.5-flash-lite": 15,  # 500 RPD
    "gemini-3.1-flash-lite": 15,  # 500 RPD
    "gemini-2.5-flash-lite": 10,  # 20 RPD
}

# How much of the nominal gap to add as headroom. The dashboard reports peak usage as a
# whole number against the limit, so a run pacing exactly at the limit has no margin for
# clock skew or a retry landing inside the same minute. 20% costs seconds on a 24-call
# run and is the difference between 4/5 and 5/5.
_PACING_HEADROOM = 1.2


def min_interval_for(model: str, *, fallback: float = DEFAULT_MIN_INTERVAL_S) -> float:
    """Seconds to leave between calls so `model` stays inside its requests-per-minute
    limit, with headroom.

    An unknown model falls back to the shared default rather than guessing generously:
    a new model is more likely to be preview-tier and *more* restricted, not less
    (ai.google.dev/gemini-api/docs/rate-limits). Being too slow costs a recording run
    some seconds; being too fast costs it the day's quota.
    """
    rpm = MODEL_RPM.get(model)
    if rpm is None or rpm <= 0:
        return fallback
    return (60.0 / rpm) * _PACING_HEADROOM


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    """Everything the client needs, resolved once so nothing reads the environment later.

    `api_key` is read from `GEMINI_API_KEY` and may be empty. An empty key is not an
    error at construction time — stub and cached modes must work end to end with the
    variable unset (docs/lanes/vc.md), so the failure belongs at the moment a live call
    is actually attempted, not at import.
    """

    api_key: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    timeout_s: float = DEFAULT_TIMEOUT_S
    # None means "derive it from the model" (see `pacing_interval_s`). An explicit value
    # still wins, so tests can pace at zero and a future key on a paid tier can be told
    # its real limit without editing the table.
    min_interval_s: float | None = None

    @classmethod
    def from_env(cls, **overrides: object) -> GeminiConfig:
        """Build from the environment. Never raises on a missing key."""
        base: dict[str, object] = {
            "api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
            "model": os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    @property
    def pacing_interval_s(self) -> float:
        """The gap this client actually paces with — explicit if given, else the one
        `self.model`'s requests-per-minute limit implies."""
        if self.min_interval_s is not None:
            return self.min_interval_s
        return min_interval_for(self.model)

    @property
    def endpoint(self) -> str:
        return f"{API_ROOT}/models/{self.model}:generateContent"


@dataclass
class GeminiClient:
    """One client, one model, one pacer.

    Holds no conversation state: each `generate()` is independent, because a governance
    agent's opinion must depend only on the evidence in front of it. Two evaluations in
    the same process must not be able to influence each other.
    """

    config: GeminiConfig = field(default_factory=GeminiConfig.from_env)
    provider: str = PROVIDER
    _pacer: Pacer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._pacer = Pacer(self.config.pacing_interval_s)

    @property
    def model(self) -> str:
        return self.config.model

    @property
    def has_key(self) -> bool:
        return self.config.has_key

    @property
    def slug(self) -> str:
        return model_slug(self.provider, self.config.model)

    def build_payload(self, prompt: Prompt) -> dict:
        """The exact JSON body sent to the API.

        Separate from `generate()` so a test can assert on the request shape without a
        network, and so the recording script can log precisely what produced a response.

        `responseSchema` is Gemini's OpenAPI-3.0 subset, not the Pydantic JSON Schema —
        see `gemini_response_schema()` for why the two differ. Sending it alongside
        `responseMimeType` is what makes malformed JSON structurally impossible rather
        than merely discouraged, which is why `parse_opinion()` still runs afterwards:
        constrained decoding guarantees shape, never sense.
        """
        return {
            "systemInstruction": {"parts": [{"text": prompt.system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "responseMimeType": "application/json",
                "responseSchema": gemini_response_schema(),
            },
        }

    def build_payload_text(self, prompt: Prompt) -> dict:
        """Same request as `build_payload`, minus the structured-output constraint.

        For a caller that wants prose, not an `AgentOpinion` — see `generate_text`.
        """
        return {
            "systemInstruction": {"parts": [{"text": prompt.system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
            "generationConfig": {"temperature": self.config.temperature},
        }

    def generate(
        self,
        prompt: Prompt,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """Send one prompt, return the model's raw text, constrained to the
        `AgentOpinion` schema (see `build_payload`).

        Paces itself first, so callers cannot accidentally burst. Raises a
        `GovernanceLLMError` subclass on every failure path; the caller decides what to
        do with `retryable`.

        `client` is injectable so tests can pass a transport rather than monkey-patching
        a module global.
        """
        return self._send(self.build_payload(prompt), client=client, timeout_s=timeout_s)

    def generate_text(
        self,
        prompt: Prompt,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """Same call as `generate`, but the response is unconstrained prose —
        for a caller that isn't asking for an `AgentOpinion` (see `base.LLMClient`).
        """
        return self._send(self.build_payload_text(prompt), client=client, timeout_s=timeout_s)

    def _send(
        self,
        payload: dict,
        *,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """The HTTP call both `generate` and `generate_text` make — pacing, the
        request itself, and error translation, shared so the two differ only in
        the payload they send.
        """
        if not self.config.has_key:
            raise LLMAuthError(
                "GEMINI_API_KEY is empty. Live calls need a key from Google AI Studio; "
                "put it in .env (which is gitignored) and never in a committed file. "
                "Stub and cached modes do not need one."
            )

        self._pacer.wait()
        headers = {
            "x-goog-api-key": self.config.api_key,
            "content-type": "application/json",
        }

        # Per call, not per client. Live mode needs a far shorter deadline than a
        # recording run, and giving it a client of its own would give it a `Pacer` of its
        # own — two pacers on one provider send at twice the rate the key allows.
        deadline = self.config.timeout_s if timeout_s is None else timeout_s

        owns_client = client is None
        http = client or httpx.Client(timeout=deadline)
        try:
            response = http.post(self.config.endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMTransportError(f"Gemini call timed out after {deadline}s: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMTransportError(f"Gemini call failed to complete: {exc}") from exc
        finally:
            if owns_client:
                http.close()

        _raise_for_status(response)
        return _extract_text(response)


def _raise_for_status(response: httpx.Response) -> None:
    """Turn an HTTP status into the exception whose `retryable` flag is correct."""
    status = response.status_code
    if status < 400:
        return

    detail = _error_message(response)

    if status == 429:
        raise LLMRateLimitError(
            f"Gemini rate limit hit (429): {detail}. The free tier allows roughly "
            f"{int(60 / DEFAULT_MIN_INTERVAL_S)} requests per minute.",
            retry_after=_retry_after(response),
        )
    if status in (401, 403):
        raise LLMAuthError(
            f"Gemini rejected the API key ({status}): {detail}. Check GEMINI_API_KEY in "
            f".env and that the key is entitled to {response.url.path.rsplit('/', 1)[-1]}."
        )
    if status >= 500:
        raise LLMTransportError(f"Gemini server error ({status}): {detail}")
    raise LLMResponseError(f"Gemini rejected the request ({status}): {detail}")


def _error_message(response: httpx.Response) -> str:
    """Pull the API's own message out, falling back to the body it actually sent."""
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
    """When the server says the window reopens — header first, then the body.

    Gemini usually sends no `Retry-After` header. It puts the advice in a
    `google.rpc.RetryInfo` entry inside the error payload instead, as a protobuf
    duration string: `{"@type": ".../RetryInfo", "retryDelay": "56.4s"}`. Reading only
    the header means every 429 falls back to a locally guessed backoff — two seconds
    against a sixty-second window, which fails three times and reports a quota error
    the server had already explained how to wait out.
    """
    raw = response.headers.get("retry-after")
    if raw is not None:
        try:
            return float(raw)
        except ValueError:
            pass

    try:
        payload = response.json()
    except ValueError:
        return None
    details = ((payload or {}).get("error") or {}).get("details") or []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        delay = detail.get("retryDelay")
        if isinstance(delay, str) and delay.endswith("s"):
            try:
                return float(delay[:-1])
            except ValueError:
                continue
    return None


def _extract_text(response: httpx.Response) -> str:
    """Dig the text out of the candidates envelope.

    Every failure here is a `LLMResponseError` carrying the reason the API gave. A
    safety block returns HTTP 200 with no candidate text, which would otherwise surface
    much later as an empty-response parse failure with nothing explaining why.
    """
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMResponseError(f"Gemini returned a non-JSON body: {exc}") from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        blocked = (payload.get("promptFeedback") or {}).get("blockReason")
        raise LLMResponseError(
            f"Gemini returned no candidates (blockReason={blocked!r}). The prompt was "
            f"filtered rather than answered."
        )

    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise LLMResponseError(
            f"Gemini returned an empty candidate "
            f"(finishReason={candidate.get('finishReason')!r})."
        )
    return text


# ---------------------------------------------------------------------------------
# Embeddings.
#
# Added for `assistant/` (the documentation retrieval index). It lives here rather
# than in a client of its own for the reason the rest of this module exists: the key
# handling, the header rule, the pacing and the error translation are already written
# and already tested, and a second integration would be a second place for the key to
# leak into a URL. Nothing above changed — `GeminiClient` and the governance panel are
# untouched by this.
# ---------------------------------------------------------------------------------

# `gemini-embedding-001`, not `gemini-embedding-2`. Both answer today and both accept
# `outputDimensionality`; this one is GA and the other two are a preview and its
# successor. The vectors are a *committed artifact* — a model that changes under the
# same name silently makes `index.json` a mixture of two embedding spaces, and cosine
# similarity across two spaces is noise that looks like a number. Stability is worth
# more here than a benchmark point.
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

# Matryoshka truncation: this model is trained so that a prefix of the full
# 3072-dimensional vector is itself a usable embedding. 768 keeps retrieval quality
# (measured against this repo's own corpus — see `assistant/index.py`) at a quarter of
# the file size, and `index.json` has to survive code review as a diff.
DEFAULT_EMBEDDING_DIMENSIONS = 768

# Requests per minute. Deliberately conservative and, unlike `MODEL_RPM` above, *not*
# read off the dashboard — the embedding models have their own quota and nobody has
# checked it for this project. This floor is sized for a *query*, which is a dozen
# tokens; the far heavier throttle a bulk build needs is a different number and lives
# with the caller doing the bulk work (`assistant/embed.py`), because it is a property
# of the volume being sent rather than of this endpoint.
EMBEDDING_RPM = 50

# The most contents one `batchEmbedContents` request may carry. The documented cap is
# 100 and 100 is the wrong number: measured on 14 Sept 2026 against this repo's own
# corpus (chunks averaging ~1,100 characters), a batch of 100 came back 429 "exceeded
# your current quota" and a batch of 50 hit the read timeout. 32 returned in ~2.2s,
# repeatedly. The published limit counts *contents*; the one that actually binds a
# free-tier key counts the tokens behind them, and nothing publishes that.
#
# A caller sending more raises rather than being silently re-batched here: splitting a
# bulk job is a decision with pacing attached, and making it invisibly would hide the
# thirty-second gap that makes the job work.
MAX_EMBED_BATCH = 32

# Which end of a retrieval pair a text is. Gemini embeds a question and a passage into
# deliberately different regions when told which is which, and passing neither costs
# real accuracy. The pair must stay matched: an index built as DOCUMENT must be
# searched as QUERY.
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_QUERY = "RETRIEVAL_QUERY"


@dataclass(frozen=True, slots=True)
class GeminiEmbeddingConfig:
    """Everything the embedding client needs, resolved once.

    Same rule as `GeminiConfig`: an empty key is not an error at construction time.
    `assistant/` loads a committed index and only needs a key to *search* or to
    rebuild, so importing it with the variable unset must work.
    """

    api_key: str = ""
    model: str = DEFAULT_EMBEDDING_MODEL
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS
    timeout_s: float = DEFAULT_TIMEOUT_S
    min_interval_s: float | None = None

    @classmethod
    def from_env(cls, **overrides: object) -> GeminiEmbeddingConfig:
        """Build from the environment. Never raises on a missing key."""
        base: dict[str, object] = {
            "api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
            "model": (
                os.environ.get("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
                or DEFAULT_EMBEDDING_MODEL
            ),
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    @property
    def pacing_interval_s(self) -> float:
        if self.min_interval_s is not None:
            return self.min_interval_s
        return (60.0 / EMBEDDING_RPM) * _PACING_HEADROOM

    @property
    def endpoint(self) -> str:
        return f"{API_ROOT}/models/{self.model}:batchEmbedContents"


@dataclass
class GeminiEmbeddingClient:
    """Text in, unit vectors out. One model, one pacer.

    **The vectors are normalised here.** Not a convenience: `gemini-embedding-001`
    returns a normalised vector only at its full 3072 dimensions, and a truncated one
    is not, so cosine similarity computed as a plain dot product would silently be
    weighted by length. Normalising at the boundary makes the client's contract "unit
    vectors" and lets everything downstream use a dot product and mean it.
    """

    config: GeminiEmbeddingConfig = field(default_factory=GeminiEmbeddingConfig.from_env)
    provider: str = PROVIDER
    _pacer: Pacer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._pacer = Pacer(self.config.pacing_interval_s)

    @property
    def model(self) -> str:
        return self.config.model

    @property
    def dimensions(self) -> int:
        return self.config.dimensions

    @property
    def has_key(self) -> bool:
        return self.config.has_key

    @property
    def slug(self) -> str:
        return model_slug(self.provider, self.config.model)

    def build_payload(self, texts: list[str], task_type: str) -> dict:
        """The exact JSON body sent to `batchEmbedContents`.

        Separate from `embed()` for the same reason `build_payload` is above: a test
        can assert on the request — including that the task type reached it — without a
        network.
        """
        return {
            "requests": [
                {
                    "model": f"models/{self.config.model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "outputDimensionality": self.config.dimensions,
                }
                for text in texts
            ]
        }

    def embed(
        self,
        texts: list[str],
        *,
        task_type: str = TASK_DOCUMENT,
        client: httpx.Client | None = None,
        timeout_s: float | None = None,
    ) -> list[list[float]]:
        """Embed up to `MAX_EMBED_BATCH` texts in one request, in order.

        Raises the same `GovernanceLLMError` subclasses as `generate()`, so a caller
        reads `retryable` and does not have to know this is a different endpoint.
        """
        if not texts:
            return []
        if len(texts) > MAX_EMBED_BATCH:
            raise ValueError(
                f"{len(texts)} texts in one embedding request; the measured ceiling is "
                f"{MAX_EMBED_BATCH}. Split the job and pace the batches — see "
                f"assistant/embed.py, which does exactly that."
            )
        if not self.config.has_key:
            raise LLMAuthError(
                "GEMINI_API_KEY is empty. Building or searching the assistant index "
                "needs a key from Google AI Studio; put it in .env (which is "
                "gitignored) and never in a committed file."
            )

        self._pacer.wait()
        headers = {
            "x-goog-api-key": self.config.api_key,
            "content-type": "application/json",
        }
        deadline = self.config.timeout_s if timeout_s is None else timeout_s

        owns_client = client is None
        http = client or httpx.Client(timeout=deadline)
        try:
            response = http.post(
                self.config.endpoint,
                json=self.build_payload(texts, task_type),
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise LLMTransportError(f"Gemini embedding timed out after {deadline}s: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMTransportError(f"Gemini embedding failed to complete: {exc}") from exc
        finally:
            if owns_client:
                http.close()

        _raise_for_status(response)
        return _extract_embeddings(response, expected=len(texts))


def _extract_embeddings(response: httpx.Response, *, expected: int) -> list[list[float]]:
    """Pull the vectors out, normalise them, and insist the count matches.

    The count check is not paranoia about the API. `batchEmbedContents` preserves
    request order and the index pairs vector `i` with chunk `i` positionally, so a
    short response would not error — it would silently attach every citation to the
    wrong passage.
    """
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMResponseError(f"Gemini returned a non-JSON body: {exc}") from exc

    raw = payload.get("embeddings")
    if not isinstance(raw, list):
        raise LLMResponseError(f"Gemini embedding response had no 'embeddings' list: {payload}")
    if len(raw) != expected:
        raise LLMResponseError(
            f"Gemini returned {len(raw)} embeddings for {expected} inputs. Vectors are "
            f"paired with chunks by position, so a mismatch would misattribute every "
            f"citation after it."
        )

    vectors: list[list[float]] = []
    for index, item in enumerate(raw):
        values = (item or {}).get("values")
        if not isinstance(values, list) or not values:
            raise LLMResponseError(f"Gemini returned an empty embedding at position {index}.")
        vectors.append(_normalise([float(v) for v in values]))
    return vectors


def _normalise(vector: list[float]) -> list[float]:
    """Scale to unit length so a dot product is a cosine.

    A zero vector cannot be normalised and should never arrive; raising beats dividing
    by zero and shipping NaNs into a similarity ranking, where they sort silently.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        raise LLMResponseError("Gemini returned a zero embedding, which cannot be normalised.")
    return [value / norm for value in vector]
