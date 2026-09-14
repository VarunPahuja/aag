"""Building, saving, loading, and the staleness guard.

Every embedding here comes from `FakeEmbedder`. Nothing in this file opens a socket.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant.chunking import Chunk
from assistant.embed import FakeEmbedder
from assistant.index import (
    REASON_CODES_SOURCE,
    Index,
    IndexStaleError,
    IndexStaleWarning,
    build_chunks,
    build_index,
    corpus_files,
    dumps,
    load_index,
    reason_code_chunks,
    save_index,
    search,
    search_vector,
    source_digests,
    stale_sources,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# --- corpus -----------------------------------------------------------------------


def test_the_adr_template_is_not_in_the_corpus(tiny_repo: Path):
    names = [p.name for p in corpus_files(tiny_repo)]
    assert "0001-example.md" in names
    assert "0000-template.md" not in names


def test_audits_are_not_in_the_corpus():
    """Point-in-time snapshots, several already wrong. An assistant quoting one as
    current tells a panel that fixed bugs are still open."""
    sources = {p.as_posix() for p in corpus_files(REPO_ROOT)}
    assert not any("/audits/" in source for source in sources)


def test_lane_briefs_are_not_in_the_corpus():
    """Excluded on purpose — four near-duplicate openings crowding a five-result
    window. If this is ever revisited, it should be revisited deliberately."""
    sources = {p.as_posix() for p in corpus_files(REPO_ROOT)}
    assert not any("/lanes/" in source for source in sources)


def test_a_missing_corpus_file_fails_loudly(tiny_repo: Path):
    (tiny_repo / "docs" / "CONTEXT.md").unlink()
    with pytest.raises(FileNotFoundError, match="CONTEXT.md"):
        corpus_files(tiny_repo)


def test_every_reason_code_becomes_its_own_chunk():
    from shared.reason_codes import HUMAN_READABLE

    chunks = reason_code_chunks(REPO_ROOT)
    # One chunk per code, plus the preamble explaining what a reason code is for.
    assert len(chunks) == len(HUMAN_READABLE) + 1
    for code, sentence in HUMAN_READABLE.items():
        chunk = next(c for c in chunks if c.heading_path[-1].endswith(f": {code}"))
        assert sentence in chunk.text
        assert chunk.source == REASON_CODES_SOURCE


def test_a_reason_code_chunk_carries_its_category():
    chunks = reason_code_chunks(REPO_ROOT)
    cooldown = next(c for c in chunks if c.heading_path[-1].endswith(": COOLDOWN_ACTIVE"))
    assert cooldown.heading_path[-1].startswith("why an increase was blocked")


# --- build / save / load ----------------------------------------------------------


def test_build_embeds_every_chunk_once(tiny_repo: Path):
    embedder = FakeEmbedder()
    index = build_index(tiny_repo, embedder=embedder)

    chunks = build_chunks(tiny_repo)
    assert len(index.chunks) == len(chunks)
    assert len(index.vectors) == len(chunks)
    assert sum(len(call) for call in embedder.document_calls) == len(chunks)
    assert embedder.query_calls == []


def test_build_embeds_the_heading_path_with_the_body(tiny_repo: Path):
    embedder = FakeEmbedder()
    build_index(tiny_repo, embedder=embedder)
    sent = [text for call in embedder.document_calls for text in call]
    assert any("ADR-0001" in text and "The policy engine decides" in text for text in sent)


def test_save_then_load_round_trips(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    path = save_index(index, tmp_path / "index.json")
    loaded = load_index(path, root=tiny_repo)

    assert loaded.chunks == index.chunks
    assert loaded.vectors == index.vectors
    assert loaded.sources == index.sources
    assert loaded.embedding_model == index.embedding_model
    assert loaded.dimensions == index.dimensions


def test_the_written_file_puts_each_vector_on_one_line(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    text = save_index(index, tmp_path / "index.json").read_text(encoding="utf-8")
    vector_lines = [line for line in text.splitlines() if line.strip().startswith('"vector"')]
    assert len(vector_lines) == len(index.chunks)
    assert json.loads(text)["chunks"][0]["vector"] == list(index.vectors[0])


def test_writing_is_stable_so_an_unchanged_rebuild_is_an_empty_diff(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    assert dumps(index) == dumps(index)


def test_a_missing_index_says_how_to_build_one(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="python -m assistant build"):
        load_index(tmp_path / "nope.json")


def test_a_future_schema_version_refuses_rather_than_guessing(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    payload = index.to_json()
    payload["schema_version"] = "99"
    path = tmp_path / "index.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_index(path, root=tiny_repo)


def test_an_unnormalised_vector_is_caught_at_load(tiny_repo: Path, tmp_path: Path):
    """`cosine()` is a bare dot product and only means anything on unit vectors."""
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    payload = index.to_json()
    payload["chunks"][0]["vector"] = [v * 3 for v in payload["chunks"][0]["vector"]]
    path = tmp_path / "index.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="norm"):
        load_index(path, root=tiny_repo)


def test_a_chunk_and_vector_count_mismatch_is_rejected():
    with pytest.raises(ValueError, match="paired by position"):
        Index(
            chunks=(Chunk(source="a.md", heading_path=("A",), text="body"),),
            vectors=(),
            sources={},
            embedding_model="fake",
            dimensions=4,
            built_at="2026-09-14T00:00:00+00:00",
        )


def test_a_rebuild_reuses_the_vectors_it_already_paid_for(tiny_repo: Path):
    """The free embedding quota counts contents, not requests — 1,000 a day. Editing
    one document must cost the chunks that changed, not the whole corpus."""
    first = build_index(tiny_repo, embedder=FakeEmbedder())

    (tiny_repo / "docs" / "adr" / "0001-example.md").write_text(
        "# ADR-0001: Statistical evidence, not LLM judgment\n\n## Decision\n\n"
        "Rewritten: the policy engine decides and the panel only advises.\n",
        encoding="utf-8",
    )

    embedder = FakeEmbedder()
    second = build_index(tiny_repo, embedder=embedder, previous=first)

    embedded = [text for call in embedder.document_calls for text in call]
    assert len(embedded) == 1
    assert "Rewritten" in embedded[0]
    assert len(second.chunks) == len(first.chunks)

    # Everything untouched keeps the exact vector it had.
    before = dict(zip([c.embedding_text for c in first.chunks], first.vectors, strict=True))
    for chunk, vector in zip(second.chunks, second.vectors, strict=True):
        if "Rewritten" not in chunk.text:
            assert vector == before[chunk.embedding_text]


def test_reuse_is_refused_across_two_embedding_models(tiny_repo: Path):
    """A file mixing two embedding spaces would still load and still search, and would
    return nonsense that looks like a number."""
    first = build_index(tiny_repo, embedder=FakeEmbedder(model="model-a"))

    embedder = FakeEmbedder(model="model-b")
    second = build_index(tiny_repo, embedder=embedder, previous=first)

    assert sum(len(call) for call in embedder.document_calls) == len(second.chunks)
    assert second.embedding_model == "model-b"


def test_reuse_is_refused_across_two_dimensionalities(tiny_repo: Path):
    first = build_index(tiny_repo, embedder=FakeEmbedder(dimensions=64))

    embedder = FakeEmbedder(dimensions=32)
    build_index(tiny_repo, embedder=embedder, previous=first)

    assert sum(len(call) for call in embedder.document_calls) == len(first.chunks)


def test_a_rebuild_with_nothing_changed_embeds_nothing(tiny_repo: Path):
    first = build_index(tiny_repo, embedder=FakeEmbedder())
    embedder = FakeEmbedder()
    second = build_index(tiny_repo, embedder=embedder, previous=first)

    assert [text for call in embedder.document_calls for text in call] == []
    assert second.vectors == first.vectors


# --- staleness --------------------------------------------------------------------


def test_a_changed_source_makes_the_loader_warn(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    path = save_index(index, tmp_path / "index.json")

    (tiny_repo / "docs" / "CONTEXT.md").write_text(
        "# CONTEXT\n\n## The core design rule\n\nSomebody rewrote this paragraph.\n",
        encoding="utf-8",
    )

    with pytest.warns(IndexStaleWarning, match="docs/CONTEXT.md: changed since the build"):
        load_index(path, root=tiny_repo)


def test_a_new_source_file_also_counts_as_stale(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    path = save_index(index, tmp_path / "index.json")

    (tiny_repo / "docs" / "adr" / "0002-added-later.md").write_text(
        "# ADR-0002: Added after the build\n\n## Decision\n\nSomething was decided.\n",
        encoding="utf-8",
    )

    with pytest.warns(IndexStaleWarning, match="added after the build"):
        load_index(path, root=tiny_repo)


def test_a_removed_source_file_also_counts_as_stale(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    (tiny_repo / "docs" / "adr" / "0001-example.md").unlink()

    problems = stale_sources(index, root=tiny_repo)
    assert problems["docs/adr/0001-example.md"] == "in the index but no longer in the corpus"


def test_line_endings_alone_do_not_make_a_source_stale(tiny_repo: Path):
    """The index is built on Windows and checked in CI on Linux, and `.gitattributes`
    says `eol=lf`. Hashing raw bytes would report every source as changed on every
    Linux checkout, and a guard that cries stale every time gets switched off."""
    index = build_index(tiny_repo, embedder=FakeEmbedder())

    path = tiny_repo / "docs" / "CONTEXT.md"
    lf = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(lf.replace(b"\n", b"\r\n"))

    assert b"\r\n" in path.read_bytes()
    assert stale_sources(index, root=tiny_repo) == {}


def test_the_written_index_uses_lf_on_every_platform(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    written = save_index(index, tmp_path / "index.json").read_bytes()
    assert b"\r\n" not in written


def test_the_reason_codes_module_is_watched_too(tiny_repo: Path):
    """It is a corpus source like any other, and it is the one that is a .py file —
    easy to forget when the rest of the list is markdown."""
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    assert REASON_CODES_SOURCE in index.sources

    path = tiny_repo / REASON_CODES_SOURCE
    path.write_text(path.read_text(encoding="utf-8") + "\n# a new comment\n", encoding="utf-8")
    assert stale_sources(index, root=tiny_repo)[REASON_CODES_SOURCE] == "changed since the build"


def test_strict_raises_instead_of_warning(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    path = save_index(index, tmp_path / "index.json")
    (tiny_repo / "docs" / "CONTEXT.md").write_text("# CONTEXT\n\nrewritten\n", encoding="utf-8")

    with pytest.raises(IndexStaleError, match="python -m assistant build"):
        load_index(path, root=tiny_repo, strict=True)


def test_a_current_index_warns_about_nothing(tiny_repo: Path, tmp_path: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    path = save_index(index, tmp_path / "index.json")

    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        load_index(path, root=tiny_repo)


def test_the_committed_index_is_current_with_the_real_docs():
    """The guard, pointed at the artifact this repository actually ships."""
    index = load_index(check_sources=False)
    assert stale_sources(index) == {}
    assert set(index.sources) == set(source_digests(REPO_ROOT))


# --- search -----------------------------------------------------------------------


def test_search_is_deterministic_for_the_same_index_and_query(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    embedder = FakeEmbedder()
    first = search(index, "what is the cooldown for", 5, embedder=embedder)
    second = search(index, "what is the cooldown for", 5, embedder=embedder)

    assert [(r.citation, r.score) for r in first] == [(r.citation, r.score) for r in second]


def test_equal_scores_break_ties_the_same_way_every_time(tiny_repo: Path):
    """Float arithmetic over the same inputs is deterministic; the order of *equal*
    scores is not, unless it is made to be."""
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    # A basis vector: most chunks miss that bucket entirely and score exactly 0.0.
    flat = [1.0] + [0.0] * (index.dimensions - 1)
    results = search_vector(index, flat, k=len(index.chunks))

    tied = [r.chunk for r in results if r.score == 0.0]
    assert len(tied) > 1, "the fixture stopped producing ties; the test proves nothing"
    assert tied == sorted(tied, key=lambda c: (c.source, c.heading_path, c.part))


def test_search_returns_k_results_with_scores(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    results = search(index, "cooldown", 3, embedder=FakeEmbedder())
    assert len(results) == 3
    assert all(-1.0001 <= r.score <= 1.0001 for r in results)
    assert results == sorted(results, key=lambda r: -r.score)


def test_search_embeds_the_query_as_a_query(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    embedder = FakeEmbedder()
    search(index, "cooldown", 2, embedder=embedder)
    assert embedder.query_calls == ["cooldown"]
    assert embedder.document_calls == []


def test_search_vector_does_no_io_and_zero_k_returns_nothing(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    assert search_vector(index, [1.0] + [0.0] * (index.dimensions - 1), k=0) == []


def test_a_query_of_the_wrong_dimensionality_says_so(tiny_repo: Path):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    with pytest.raises(ValueError, match="different models"):
        search_vector(index, [1.0, 0.0], k=1)
