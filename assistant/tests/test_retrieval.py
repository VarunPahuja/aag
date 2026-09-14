"""Does a real question actually retrieve the paragraph it should?

This is the test that matters, and it is the one a fake embedder cannot write. A
bag-of-words stand-in proves the plumbing carries a vector from one end to the other;
it proves nothing about whether "what stops the LLM from raising a limit on its own"
lands on ADR-0003, because that depends entirely on the embedding model.

So the query vectors are **recorded**, exactly the way this project records model
responses rather than calling a model from a test (`governance/llm/recording.py`). The
five verification questions and four deliberately off-topic ones were embedded once on
14 Sept 2026 with `gemini-embedding-001` at 768 dimensions, and live in
`query_vectors.json`. Nothing here opens a socket; everything here is measured against
the index this repository actually ships.

If the index is rebuilt with a different embedding model, the recordings and the index
are in two different vector spaces and every number below is meaningless. That is not
left to trust: the fixture carries its model and dimensionality and this module refuses
to run against an index that disagrees.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant.index import RELEVANCE_THRESHOLD, load_index, search_vector

FIXTURE = Path(__file__).resolve().parent / "query_vectors.json"

# question -> the citations that are a correct first result.
#
# A set rather than a single value, because two of these questions have two right
# answers and pinning either one would be pinning an accident. "Why the Wilson lower
# bound" is answered by the glossary entry that defines it *and* by ADR-0002's
# reasoning about why it beats the Wald interval; "what is the cooldown for" by the
# glossary entry and by the reason code the policy engine emits. What would be a
# failure is any of them returning something from a third document.
ANSWERABLE: dict[str, set[str]] = {
    "why do you use the Wilson lower bound instead of accuracy": {
        "docs/adr/0002-wilson-score-interval-over-wald.md",
        "docs/SYSTEM-EXPLAINED.md",
    },
    "what stops the LLM from raising a limit on its own": {
        "docs/adr/0003-deterministic-policy-engine-as-enforcement-boundary.md",
    },
    "where does ground truth come from in production": {
        "docs/adr/0009-post-hoc-audit-sampling-as-ground-truth.md",
    },
    "why do clawbacks not need human approval": {
        "docs/adr/0004-human-approval-required-for-autonomy-increases.md",
    },
    "what is the cooldown for": {"shared/reason_codes.py", "docs/SYSTEM-EXPLAINED.md"},
}

UNANSWERABLE = [
    "how do I bake sourdough bread",
    "what is our Kubernetes ingress configuration",
    "who won the 2024 cricket world cup",
    "how do I rotate the TLS certificate on the load balancer",
]


@pytest.fixture(scope="module")
def recorded() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def index(recorded: dict):
    loaded = load_index(check_sources=False)
    if (loaded.embedding_model, loaded.dimensions) != (
        recorded["model"],
        recorded["dimensions"],
    ):
        pytest.fail(
            f"index.json was built with {loaded.embedding_model} at "
            f"{loaded.dimensions}d but the recorded queries are "
            f"{recorded['model']} at {recorded['dimensions']}d. Two vector spaces; "
            f"the similarities below would be noise. Re-record the fixture."
        )
    return loaded


@pytest.mark.parametrize("question", sorted(ANSWERABLE))
def test_a_real_question_retrieves_the_document_it_should(question, index, recorded):
    top = search_vector(index, recorded["queries"][question], k=1)[0]
    assert top.chunk.source in ANSWERABLE[question], (
        f"{question!r} returned {top.citation} at {top.score:.3f}; "
        f"expected something from {sorted(ANSWERABLE[question])}"
    )


@pytest.mark.parametrize("question", sorted(ANSWERABLE))
def test_a_real_question_clears_the_relevance_threshold(question, index, recorded):
    top = search_vector(index, recorded["queries"][question], k=1)[0]
    assert top.is_relevant, f"{question!r} scored {top.score:.3f}"


def test_wilson_surfaces_adr_0002_with_its_reasoning_not_just_a_definition(index, recorded):
    """A definition says what the Wilson bound *is*. The question asks why it is used
    instead of accuracy, and the answer to that is ADR-0002's argument — so the
    argument has to come back too, in its own named sections, not be crowded out by
    the glossary entry that shares its vocabulary."""
    question = "why do you use the Wilson lower bound instead of accuracy"
    results = search_vector(index, recorded["queries"][question], k=5)

    adr = [r for r in results if "0002-wilson" in r.chunk.source]
    assert len(adr) >= 3
    assert {"Context", "Decision"} <= {r.chunk.heading_path[-1] for r in adr}
    assert all(r.is_relevant for r in adr)


def test_the_glossary_answers_a_term_question_with_the_term(index, recorded):
    """Before definitions were split out, the glossary chunk holding the cooldown
    definition ranked fifth at 0.611 — below the threshold, behind three one-line
    reason codes — because its embedding averaged twenty-five unrelated terms."""
    question = "what is the cooldown for"
    results = search_vector(index, recorded["queries"][question], k=5)

    cooldown = next(r for r in results if r.chunk.heading_path[-1] == "Cooldown")
    assert cooldown.citation == "System Explained > 3. Glossary > Cooldown"
    assert cooldown.is_relevant
    assert "COOLDOWN_BETWEEN_INCREASES" in cooldown.chunk.text


def test_hallucination_question_surfaces_the_hard_ceiling(index, recorded):
    """'What happens if the LLM hallucinates' has one correct answer in this system:
    deterministic code clamps whatever it proposed. Whichever document is cited, the
    clamp has to be in the text that comes back."""
    question = "what stops the LLM from raising a limit on its own"

    results = search_vector(index, recorded["queries"][question], k=5)
    joined = " ".join(r.chunk.text.lower() for r in results)
    assert "policy engine" in joined
    assert any(word in joined for word in ("ceiling", "clamp", "enforce"))


@pytest.mark.parametrize("question", UNANSWERABLE)
def test_a_question_the_docs_do_not_answer_stays_under_the_threshold(question, index, recorded):
    """The failure this index exists to prevent: a fluent answer about a system the
    corpus has no text about, assembled from a chunk that shares three words with the
    question."""
    top = search_vector(index, recorded["queries"][question], k=1)[0]
    assert not top.is_relevant, (
        f"{question!r} scored {top.score:.3f} on {top.citation}, above the "
        f"{RELEVANCE_THRESHOLD} threshold — it would be served as an answer"
    )


def test_the_threshold_sits_in_the_gap_the_measurements_found(index, recorded):
    """Pins the separation the threshold depends on, so shrinking it is a test failure
    rather than a quiet degradation."""
    answerable = [search_vector(index, recorded["queries"][q], k=1)[0].score for q in ANSWERABLE]
    unanswerable = [search_vector(index, recorded["queries"][q], k=1)[0].score for q in UNANSWERABLE]

    assert max(unanswerable) < RELEVANCE_THRESHOLD < min(answerable)
    assert min(answerable) - max(unanswerable) > 0.05


def test_every_recorded_query_is_one_of_the_questions_under_test(recorded):
    """A fixture with strays in it is a fixture nobody is maintaining."""
    assert set(recorded["queries"]) == set(ANSWERABLE) | set(UNANSWERABLE)
