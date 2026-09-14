"""Chunking: heading boundaries, heading paths, and the things that look like
headings but are not."""

from __future__ import annotations

from pathlib import Path

from assistant.chunking import (
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    Chunk,
    chunk_file,
    chunk_markdown,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

ADR = """# ADR-0002: Wilson score interval over the Wald interval

## Status

Accepted, and the reasoning below is what a reviewer should read first.

## Context

The Wald interval is the one everybody learns. It is also wrong at the sample
sizes that matter here, where an agent has made forty decisions and got all
forty right.

## Decision

Use the Wilson score interval's lower bound as the evidence an increase is
measured against. It does not collapse at p = 1.

## Consequences

An agent with a perfect record still has to accumulate a sample before the
bound clears the gate.
"""


def test_each_heading_starts_a_new_chunk():
    chunks = chunk_markdown(ADR, source="docs/adr/0002.md")
    trails = [chunk.heading_path[-1] for chunk in chunks]
    assert trails == ["Status", "Context", "Decision", "Consequences"]


def test_a_section_stops_at_the_next_heading():
    chunks = chunk_markdown(ADR, source="docs/adr/0002.md")
    context = next(c for c in chunks if c.heading_path[-1] == "Context")
    assert "forty right" in context.text
    # The whole point: Context must not swallow Decision.
    assert "Wilson score interval's lower bound" not in context.text


def test_heading_path_keeps_its_ancestors():
    chunks = chunk_markdown(ADR, source="docs/adr/0002.md")
    decision = next(c for c in chunks if c.heading_path[-1] == "Decision")
    assert decision.heading_path == (
        "ADR-0002: Wilson score interval over the Wald interval",
        "Decision",
    )
    assert decision.citation.endswith("> Decision")


def test_a_deeper_subsection_nests_rather_than_replacing():
    text = "# Doc\n\n" + "a" * 40 + "\n\n## Section\n\n" + "b" * 40 + "\n\n### Detail\n\n" + "c" * 40
    chunks = chunk_markdown(text, source="doc.md")
    assert [c.heading_path for c in chunks] == [
        ("Doc",),
        ("Doc", "Section"),
        ("Doc", "Section", "Detail"),
    ]


def test_a_sibling_heading_pops_back_to_the_right_level():
    text = (
        "# Doc\n\n## One\n\n### Deep\n\n" + "a" * 40 + "\n\n## Two\n\n" + "b" * 40
    )
    chunks = chunk_markdown(text, source="doc.md")
    assert chunks[-1].heading_path == ("Doc", "Two")


def test_a_comment_inside_a_code_fence_is_not_a_heading():
    text = (
        "# Doc\n\n## Commands\n\n```bash\n# this is a shell comment, not a heading\n"
        "pytest -q\n```\n\nRun it from the repo root with the project venv active.\n"
    )
    chunks = chunk_markdown(text, source="doc.md")
    assert [c.heading_path[-1] for c in chunks] == ["Commands"]
    assert "shell comment" in chunks[0].text


def test_the_heading_path_travels_with_the_text_into_the_embedding():
    chunk = Chunk(source="docs/adr/0006.md", heading_path=("ADR-0006", "Decision"), text="body")
    assert "docs/adr/0006.md" in chunk.embedding_text
    assert "ADR-0006 > Decision" in chunk.embedding_text
    assert chunk.embedding_text.endswith("body")


def test_a_heading_with_nothing_under_it_is_dropped():
    text = "# Doc\n\n## Status\n\nAccepted\n\n## Context\n\n" + "a" * 200
    chunks = chunk_markdown(text, source="doc.md")
    assert len("Accepted") < MIN_CHUNK_CHARS
    assert [c.heading_path[-1] for c in chunks] == ["Context"]


def test_a_long_section_splits_on_paragraphs_not_mid_sentence():
    paragraph = ("Wilson holds at the boundary because the interval is not symmetric. " * 6).strip()
    text = "# Doc\n\n## Long\n\n" + "\n\n".join([paragraph] * 6)
    chunks = chunk_markdown(text, source="doc.md")

    assert len(chunks) > 1
    assert [c.part for c in chunks] == list(range(1, len(chunks) + 1))
    assert all(c.heading_path == ("Doc", "Long") for c in chunks)
    # Every piece is whole paragraphs: nothing starts or ends mid-sentence.
    for chunk in chunks:
        assert chunk.text.startswith("Wilson holds")
        assert chunk.text.endswith("symmetric.")


def test_an_over_long_table_splits_by_row_and_keeps_its_header():
    header = "| Lane | Owner | What it does |\n|---|---|---|"
    row = "| Lane {n} | Someone | " + "a long description of the lane " * 12 + "|"
    text = "# Doc\n\n## Status\n\n" + header + "\n" + "\n".join(row.format(n=n) for n in range(8))
    chunks = chunk_markdown(text, source="doc.md")

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.startswith("| Lane | Owner | What it does |")
    # Each row survives in exactly one chunk.
    for n in range(8):
        assert sum(f"| Lane {n} |" in c.text for c in chunks) == 1


def test_a_glossary_definition_becomes_its_own_chunk_named_after_its_term():
    """Markdown has no definition-list syntax, so a heading splitter alone packs
    twenty-five unrelated terms into a handful of chunks whose embeddings are about
    nothing in particular."""
    text = (
        "# Doc\n\n## Glossary\n\n"
        "**Rung** - one of the five fixed positions on the autonomy ladder.\n\n"
        "**Cooldown** - the minimum number of decisions between autonomy increases, "
        "so a lucky streak right after a promotion cannot trigger another.\n\n"
        "**Drift** - a statistically supported drop in recent accuracy.\n"
    )
    chunks = chunk_markdown(text, source="doc.md")

    assert [c.heading_path[-1] for c in chunks] == ["Rung", "Cooldown", "Drift"]
    assert [c.citation for c in chunks][1] == "Doc > Glossary > Cooldown"
    assert all(c.part == 0 for c in chunks)
    assert "Rung" not in chunks[1].text


def test_what_follows_a_definition_stays_attached_to_it():
    """The Wilson glossary entry is a paragraph, then more prose, then a table. All of
    it explains that one term."""
    text = (
        "# Doc\n\n## Glossary\n\n"
        "**Wilson lower bound** - the low end of a confidence interval on a proportion.\n\n"
        "| Record | Point accuracy | Wilson lower bound |\n|---|---|---|\n"
        "| 10 / 10 | 100% | ~72.2% |\n\n"
        "**Cooldown** - the minimum number of decisions between increases, so a lucky "
        "streak cannot immediately trigger another one.\n"
    )
    chunks = chunk_markdown(text, source="doc.md")

    assert [c.heading_path[-1] for c in chunks] == ["Wilson lower bound", "Cooldown"]
    assert "~72.2%" in chunks[0].text
    assert "~72.2%" not in chunks[1].text


def test_a_bold_lead_in_that_is_not_a_definition_does_not_split():
    """`**Note** that ...` is emphasis, not a definition; only a bold run followed by a
    dash is treated as a term."""
    text = "# Doc\n\n## Section\n\n**Note** that this is emphasis, not a glossary entry.\n\n"
    text += "**Also** this one is not a definition either, so the section stays whole.\n"
    chunks = chunk_markdown(text, source="doc.md")
    assert len(chunks) == 1


def test_a_single_over_long_paragraph_is_kept_whole():
    # An over-long chunk is a worse embedding; a severed sentence is a worse quote.
    paragraph = "x" * (MAX_CHUNK_CHARS + 500)
    chunks = chunk_markdown(f"# Doc\n\n## Long\n\n{paragraph}", source="doc.md")
    assert len(chunks) == 1
    assert chunks[0].text == paragraph


def test_text_before_the_first_heading_is_kept_and_cites_the_file():
    text = "This document has a preamble before anything else, and it matters.\n\n# Doc\n\n" + "a" * 50
    chunks = chunk_markdown(text, source="docs/CONTEXT.md")
    assert chunks[0].heading_path == ()
    assert chunks[0].citation == "docs/CONTEXT.md"


def test_horizontal_rules_are_dropped():
    text = "# Doc\n\n## Section\n\n---\n\n" + "a" * 60 + "\n\n---\n"
    chunks = chunk_markdown(text, source="doc.md")
    assert "---" not in chunks[0].text


def test_chunk_json_round_trips():
    chunk = Chunk(source="a.md", heading_path=("A", "B"), text="body", part=2)
    assert Chunk.from_json(chunk.to_json()) == chunk


def test_real_adr_splits_into_its_four_argument_sections():
    """The whole design claim, against a real file: Context, Decision, Consequences
    and Alternatives each come back as one unit. `Status` is dropped — its body is the
    single word "Accepted"."""
    path = REPO_ROOT / "docs" / "adr" / "0002-wilson-score-interval-over-wald.md"
    chunks = chunk_file(path, root=REPO_ROOT)

    assert [c.heading_path[-1] for c in chunks] == [
        "Context",
        "Decision",
        "Consequences",
        "Alternatives considered",
    ]
    assert all(c.source == "docs/adr/0002-wilson-score-interval-over-wald.md" for c in chunks)
    assert all(c.heading_path[0].startswith("ADR-0002") for c in chunks)
