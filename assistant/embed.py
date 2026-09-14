"""The embedding call, behind the provider layer this project already has.

There is exactly one LLM integration in this repository — `governance/llm/` — and this
module does not add a second. `GeminiEmbeddingClient` lives in `governance/llm/gemini.py`
beside the client it shares its key handling, header rule, `Pacer` and error hierarchy
with; everything here is the seam: which provider answers, what a caller may assume
about the vectors, and a fake for tests.

**Gemini only, for now, and that is a decision rather than an omission.** Provider
choice is resolved through `governance.llm.registry.resolve_provider`, so the same
`GOVERNANCE_PROVIDER` that picks a panel model is read here too — but Anthropic ships no
embedding model at all, and OpenAI's is a paid API. `docs/lanes/vc.md` forbids
introducing a paid service and ADR-0012's ruling on the optional paid *chat* providers
is still Proposed; quietly making a paid embedding endpoint the thing that builds a
committed artifact would settle that question by accident. Selecting another provider
raises, loudly, naming the reason.

**One client per provider, cached.** Same rule as the registry it borrows from: a rate
limit belongs to the key, not to the caller, and a second client would bring a second
`Pacer` with no memory of the last request.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import cache
from typing import Protocol, runtime_checkable

from governance.llm.errors import GovernanceLLMError
from governance.llm.gemini import (
    MAX_EMBED_BATCH,
    TASK_DOCUMENT,
    TASK_QUERY,
    GeminiEmbeddingClient,
)
from governance.llm.gemini import PROVIDER as GEMINI
from governance.llm.registry import resolve_provider

# Three attempts, not more. A build is small enough that failing fast and being run
# again beats a long automatic grind, and a rate limit that survives three tries is a
# daily quota rather than a burst — no amount of local retrying fixes that.
MAX_ATTEMPTS = 3
RETRY_BASE_DELAY_S = 2.0

# Bulk-build throttling. The batch size is the client's measured per-request ceiling;
# the interval is what a whole corpus needs between requests to stay inside the
# free tier's per-minute token quota. See `GeminiEmbedder.embed_documents`.
DOCUMENT_BATCH_SIZE = MAX_EMBED_BATCH
DOCUMENT_BATCH_INTERVAL_S = 30.0

__all__ = [
    "DOCUMENT_BATCH_INTERVAL_S",
    "DOCUMENT_BATCH_SIZE",
    "MAX_ATTEMPTS",
    "TASK_DOCUMENT",
    "TASK_QUERY",
    "Embedder",
    "EmbeddingsUnsupportedError",
    "FakeEmbedder",
    "build_embedder",
    "cosine",
    "reset_embedders",
]


class EmbeddingsUnsupportedError(GovernanceLLMError):
    """A provider was selected that this project has no free embedding model for.

    Not retryable. Raising rather than silently falling back to Gemini, for the reason
    `UnknownProviderError` raises: an index built by a provider nobody chose looks
    exactly like one built by the provider they did choose.
    """

    retryable = False


@runtime_checkable
class Embedder(Protocol):
    """Text in, unit vectors out.

    Two methods rather than one because retrieval models embed a *question* and a
    *passage* differently on purpose, and mixing the two ends up matching questions to
    questions. The index records which model produced it so a search cannot be run
    against vectors from another one.
    """

    @property
    def model(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class GeminiEmbedder:
    """`Embedder` over `GeminiEmbeddingClient`, fixing the task type at each end.

    Retries a *retryable* failure, reading `GovernanceLLMError.retryable` rather than
    matching exception types — same rule live mode follows, and for the same reason: a
    new failure mode gets the right behaviour by declaring it. A build is only four
    requests, but it is four requests against a free tier over a network that produced
    both a 429 and a DNS failure while this was being written. Losing the whole build
    to one of them, after the other three succeeded and the two minutes were already
    spent, is exactly what a two-second wait avoids.

    An auth error is not retried: `retryable` is False on it, the key will still be
    missing on the second attempt, and three silent retries is how a developer concludes
    the API is down.
    """

    def __init__(
        self,
        client: GeminiEmbeddingClient | None = None,
        *,
        attempts: int = MAX_ATTEMPTS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client or GeminiEmbeddingClient()
        self._attempts = max(1, attempts)
        self._sleep = sleep

    @property
    def model(self) -> str:
        return self._client.model

    @property
    def dimensions(self) -> int:
        return self._client.dimensions

    @property
    def has_key(self) -> bool:
        return self._client.has_key

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed the whole corpus, in batches, slowly.

        **The thirty seconds between batches is measured, not cautious.** Four batches
        of 32 sent back to back — six seconds apart, well inside any published
        requests-per-minute figure — return 429 "you exceeded your current quota". The
        same four batches thirty seconds apart all succeed. The limit that binds here
        counts tokens per minute, not requests, and Google publishes no number for it,
        so this is the gap that was observed to work with room under it.

        It makes a build take about two minutes. That is the right trade for something
        run by hand when the docs change: the alternative is a build that dies on its
        third batch having already spent the first two.
        """
        vectors: list[list[float]] = []
        for start in range(0, len(texts), DOCUMENT_BATCH_SIZE):
            if start:
                self._sleep(DOCUMENT_BATCH_INTERVAL_S)
            batch = texts[start : start + DOCUMENT_BATCH_SIZE]
            vectors.extend(
                self._with_retry(lambda b=batch: self._client.embed(b, task_type=TASK_DOCUMENT))
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._with_retry(lambda: self._client.embed([text], task_type=TASK_QUERY))[0]

    def _with_retry(self, call: Callable[[], list[list[float]]]) -> list[list[float]]:
        last: GovernanceLLMError | None = None
        for attempt in range(1, self._attempts + 1):
            try:
                return call()
            except GovernanceLLMError as exc:
                if not exc.retryable or attempt == self._attempts:
                    raise
                last = exc
                self._sleep(_backoff(exc, attempt))
        raise last  # pragma: no cover - unreachable, the loop either returns or raises


def _backoff(error: GovernanceLLMError, attempt: int) -> float:
    """Seconds to wait before the next attempt.

    The server's own `retry-after` wins when it sends one: it knows when the window
    reopens and we are guessing. Otherwise doubling from two seconds, which clears a
    transient DNS or 5xx blip without turning a build into a coffee break.
    """
    advice = getattr(error, "retry_after", None)
    if isinstance(advice, int | float) and advice > 0:
        return float(advice)
    return RETRY_BASE_DELAY_S * (2 ** (attempt - 1))


@cache
def _embedder_for(provider: str) -> Embedder:
    if provider != GEMINI:
        raise EmbeddingsUnsupportedError(
            f"provider {provider!r} has no embedding model this project may use: "
            f"Anthropic publishes none, and OpenAI's is a paid API that "
            f"docs/lanes/vc.md forbids introducing (ADR-0012 is still Proposed). "
            f"Set GOVERNANCE_PROVIDER=gemini to build or search the assistant index."
        )
    return GeminiEmbedder()


def build_embedder(*, provider: str | None = None) -> Embedder:
    """The embedder for the configured provider. Never raises on a missing key.

    A missing key fails at the moment a call is made, not here, so `load_index()` and
    every test that does not embed anything work with `GEMINI_API_KEY` unset.
    """
    return _embedder_for(resolve_provider(default=provider))


def reset_embedders() -> None:
    """Drop the cached embedders so a changed environment is picked up. For tests."""
    _embedder_for.cache_clear()


def cosine(left: list[float], right: list[float]) -> float:
    """Cosine similarity of two *unit* vectors, i.e. their dot product.

    Deliberately not re-normalising. Both clients return unit vectors and the index
    stores them that way, so dividing by a norm of 1.0 on every one of a few hundred
    comparisons buys nothing — and if a vector ever arrives un-normalised, a score
    quietly outside [-1, 1] is a better signal than a wrong ranking that looks fine.
    `Index.load` checks the norms once, at load, where it can say so.
    """
    if len(left) != len(right):
        raise ValueError(
            f"cannot compare a {len(left)}-dimensional vector with a "
            f"{len(right)}-dimensional one — the index and the query were embedded by "
            f"different models or at different output dimensionalities."
        )
    return sum(a * b for a, b in zip(left, right, strict=True))


class FakeEmbedder:
    """A deterministic `Embedder` for tests. No network, ever.

    Hashes each token into a fixed number of buckets — a bag-of-words vector, which is
    enough to make "the chunk containing these words scores higher" true without
    pretending to be a language model. Tests that assert on *retrieval quality* need a
    real model and are therefore not tests; that claim is checked by building the index
    for real and reading the results, and the numbers are in `assistant/index.py`.
    """

    def __init__(self, dimensions: int = 64, model: str = "fake-embedder") -> None:
        self._dimensions = dimensions
        self._model = model
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        counts = [0.0] * self._dimensions
        for token in text.lower().split():
            word = "".join(c for c in token if c.isalnum())
            if word:
                counts[hash_token(word) % self._dimensions] += 1.0
        norm = sum(value * value for value in counts) ** 0.5
        if norm == 0.0:
            counts[0] = 1.0
            return counts
        return [value / norm for value in counts]


def hash_token(word: str) -> int:
    """A stable hash. `hash()` is salted per process, so it cannot be used here —
    a fake embedder that changes under `PYTHONHASHSEED` would make the determinism
    test pass or fail by luck."""
    value = 0
    for char in word:
        value = (value * 131 + ord(char)) % 1_000_003
    return value
