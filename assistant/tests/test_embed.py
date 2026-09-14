"""The embedding seam: the request that goes out, the vectors that come back, and
what happens when the call fails.

`httpx.MockTransport` throughout — a transport is passed in rather than a module
global monkey-patched, so these tests assert on the real client with no network.
"""

from __future__ import annotations

import httpx
import pytest

from assistant.embed import (
    DOCUMENT_BATCH_INTERVAL_S,
    DOCUMENT_BATCH_SIZE,
    EmbeddingsUnsupportedError,
    FakeEmbedder,
    GeminiEmbedder,
    build_embedder,
    cosine,
    hash_token,
    reset_embedders,
)
from governance.llm.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTransportError,
)
from governance.llm.gemini import (
    MAX_EMBED_BATCH,
    TASK_DOCUMENT,
    TASK_QUERY,
    GeminiEmbeddingClient,
    GeminiEmbeddingConfig,
)


def client(**overrides) -> GeminiEmbeddingClient:
    config = GeminiEmbeddingConfig(
        api_key=overrides.pop("api_key", "test-key"),
        dimensions=overrides.pop("dimensions", 4),
        min_interval_s=0.0,
        **overrides,
    )
    return GeminiEmbeddingClient(config)


def transport(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def responding(vectors: list[list[float]], captured: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["request"] = request
        return httpx.Response(200, json={"embeddings": [{"values": v} for v in vectors]})

    return handler


# --- the request ------------------------------------------------------------------


def test_the_payload_names_the_model_task_and_dimensionality():
    payload = client().build_payload(["alpha", "beta"], TASK_DOCUMENT)
    assert len(payload["requests"]) == 2
    first = payload["requests"][0]
    assert first["model"] == "models/gemini-embedding-001"
    assert first["content"]["parts"][0]["text"] == "alpha"
    assert first["taskType"] == TASK_DOCUMENT
    assert first["outputDimensionality"] == 4


def test_the_key_travels_in_a_header_and_never_in_the_url():
    captured: dict = {}
    with transport(responding([[1.0, 0.0, 0.0, 0.0]], captured)) as http:
        client().embed(["alpha"], client=http)
    request = captured["request"]
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "test-key" not in str(request.url)


def test_a_query_is_embedded_as_a_query_and_a_document_as_a_document():
    captured: dict = {}
    gemini = client()
    with transport(responding([[1.0, 0.0, 0.0, 0.0]], captured)) as http:
        gemini.embed(["q"], task_type=TASK_QUERY, client=http)
        assert TASK_QUERY in captured["request"].read().decode()

        gemini.embed(["d"], task_type=TASK_DOCUMENT, client=http)
        body = captured["request"].read().decode()
        assert TASK_DOCUMENT in body and TASK_QUERY not in body


def test_more_texts_than_the_measured_ceiling_is_refused_before_the_call():
    with pytest.raises(ValueError, match=str(MAX_EMBED_BATCH)):
        client().embed(["x"] * (MAX_EMBED_BATCH + 1))


def test_an_empty_list_makes_no_call_at_all():
    def explode(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be made for an empty batch")

    with transport(explode) as http:
        assert client().embed([], client=http) == []


def test_a_missing_key_fails_before_the_network():
    def explode(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be made without a key")

    with transport(explode) as http, pytest.raises(LLMAuthError, match="GEMINI_API_KEY"):
        client(api_key="").embed(["alpha"], client=http)


# --- the response -----------------------------------------------------------------


def test_vectors_come_back_normalised():
    """Truncated Gemini embeddings are not unit length, and `cosine()` is a bare dot
    product. Normalising at the boundary is what makes the rest of the code honest."""
    with transport(responding([[3.0, 4.0, 0.0, 0.0]])) as http:
        (vector,) = client().embed(["alpha"], client=http)
    assert vector == pytest.approx([0.6, 0.8, 0.0, 0.0])
    assert cosine(vector, vector) == pytest.approx(1.0)


def test_a_short_response_is_an_error_not_a_silent_misalignment():
    """Vectors are paired with chunks by position. Two vectors for three chunks would
    not crash — it would attach every citation after the gap to the wrong passage."""
    with transport(responding([[1.0, 0.0, 0.0, 0.0]])) as http, pytest.raises(LLMResponseError, match="misattribute"):
        client().embed(["a", "b", "c"], client=http)


def test_a_zero_vector_is_refused_rather_than_producing_nans():
    with transport(responding([[0.0, 0.0, 0.0, 0.0]])) as http, pytest.raises(LLMResponseError, match="zero embedding"):
        client().embed(["alpha"], client=http)


def test_a_body_with_no_embeddings_list_says_so():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"nothing": "useful"})

    with transport(handler) as http, pytest.raises(LLMResponseError, match="no 'embeddings' list"):
        client().embed(["alpha"], client=http)


@pytest.mark.parametrize(
    ("status", "expected", "retryable"),
    [
        (429, LLMRateLimitError, True),
        (401, LLMAuthError, False),
        (403, LLMAuthError, False),
        (503, LLMTransportError, True),
        (400, LLMResponseError, False),
    ],
)
def test_http_status_becomes_the_error_whose_retryable_flag_is_right(
    status, expected, retryable
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "nope"}})

    with transport(handler) as http, pytest.raises(expected) as caught:
        client().embed(["alpha"], client=http)
    assert caught.value.retryable is retryable


# --- retry and pacing -------------------------------------------------------------


class _Recording:
    """A stand-in `GeminiEmbeddingClient` that plays a scripted sequence."""

    def __init__(self, script: list, dimensions: int = 4) -> None:
        self.script = list(script)
        self.calls: list[list[str]] = []
        self.model = "fake-gemini"
        self.dimensions = dimensions
        self.has_key = True

    def embed(self, texts, *, task_type=TASK_DOCUMENT, **_):
        self.calls.append(list(texts))
        outcome = self.script.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


def test_a_retryable_failure_is_retried():
    inner = _Recording([LLMRateLimitError("429"), None])
    slept: list[float] = []
    embedder = GeminiEmbedder(inner, sleep=slept.append)

    assert embedder.embed_query("alpha") == [1.0, 0.0, 0.0, 0.0]
    assert len(inner.calls) == 2
    assert slept == [2.0]


def test_the_servers_own_retry_after_wins_over_the_local_guess():
    inner = _Recording([LLMRateLimitError("429", retry_after=17.0), None])
    slept: list[float] = []
    GeminiEmbedder(inner, sleep=slept.append).embed_query("alpha")
    assert slept == [17.0]


def test_the_retry_delay_is_read_out_of_geminis_error_body():
    """Gemini sends no `Retry-After` header; it puts a `google.rpc.RetryInfo` entry in
    the error payload. Reading only the header means every 429 falls back to a guessed
    two-second backoff against a sixty-second window, fails three times, and reports a
    quota error the server had already explained how to wait out."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "Quota exceeded for metric: embed_content_free_tier_requests",
                    "details": [
                        {"@type": "type.googleapis.com/google.rpc.QuotaFailure"},
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "56.4s",
                        },
                    ],
                }
            },
        )

    with transport(handler) as http, pytest.raises(LLMRateLimitError) as caught:
        client().embed(["alpha"], client=http)
    assert caught.value.retry_after == pytest.approx(56.4)


def test_a_429_with_no_advice_at_all_still_raises_cleanly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    with transport(handler) as http, pytest.raises(LLMRateLimitError) as caught:
        client().embed(["alpha"], client=http)
    assert caught.value.retry_after is None


def test_an_unretryable_failure_is_not_retried():
    """Three silent retries on a missing key is how a developer concludes the API is
    down."""
    inner = _Recording([LLMAuthError("no key")])
    slept: list[float] = []
    with pytest.raises(LLMAuthError):
        GeminiEmbedder(inner, sleep=slept.append).embed_query("alpha")
    assert len(inner.calls) == 1
    assert slept == []


def test_retries_give_up_and_raise_the_real_error():
    inner = _Recording([LLMRateLimitError("429")] * 3)
    with pytest.raises(LLMRateLimitError):
        GeminiEmbedder(inner, attempts=3, sleep=lambda _: None).embed_query("alpha")
    assert len(inner.calls) == 3


def test_a_corpus_is_batched_and_paced():
    """The 30s gap is what makes a full build survive the free tier's per-minute token
    quota — four batches six seconds apart return 429."""
    count = DOCUMENT_BATCH_SIZE * 2 + 5
    inner = _Recording([None, None, None])
    slept: list[float] = []
    vectors = GeminiEmbedder(inner, sleep=slept.append).embed_documents(["x"] * count)

    assert len(vectors) == count
    assert [len(call) for call in inner.calls] == [
        DOCUMENT_BATCH_SIZE,
        DOCUMENT_BATCH_SIZE,
        5,
    ]
    # Between batches, never before the first.
    assert slept == [DOCUMENT_BATCH_INTERVAL_S, DOCUMENT_BATCH_INTERVAL_S]


# --- provider selection -----------------------------------------------------------


def test_gemini_is_the_default_provider(monkeypatch):
    monkeypatch.delenv("GOVERNANCE_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    reset_embedders()
    try:
        assert build_embedder().model == "gemini-embedding-001"
    finally:
        reset_embedders()


def test_a_paid_provider_is_refused_with_the_reason(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "openai")
    reset_embedders()
    try:
        with pytest.raises(EmbeddingsUnsupportedError, match="paid API"):
            build_embedder()
    finally:
        reset_embedders()


def test_one_embedder_per_provider_so_one_pacer_per_key(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_PROVIDER", "gemini")
    reset_embedders()
    try:
        assert build_embedder() is build_embedder()
    finally:
        reset_embedders()


# --- cosine and the fake ----------------------------------------------------------


def test_cosine_refuses_to_compare_two_different_vector_spaces():
    with pytest.raises(ValueError, match="different models"):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


def test_the_fake_embedder_is_stable_across_processes():
    """`hash()` is salted per run. A fake that used it would make the determinism test
    pass or fail by luck."""
    assert hash_token("wilson") == hash_token("wilson")
    assert hash_token("wilson") != hash_token("wald")

    embedder = FakeEmbedder()
    assert embedder.embed_query("cooldown") == embedder.embed_query("cooldown")
    assert cosine(embedder.embed_query("cooldown"), embedder.embed_query("cooldown")) == (
        pytest.approx(1.0)
    )


def test_the_fake_embedder_returns_unit_vectors_even_for_empty_text():
    vector = FakeEmbedder().embed_query("")
    assert cosine(vector, vector) == pytest.approx(1.0)
