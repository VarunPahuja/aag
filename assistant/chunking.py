"""Splitting a markdown document into units worth retrieving.

**Headings, not character counts.** A 500-character window is the obvious
implementation and the wrong one here. An ADR's `Context`, `Decision` and
`Consequences` are each a complete argument; a fixed window cuts one of them in half
and hands the assistant the first paragraph of a reason with the conclusion missing.
The author already marked where the ideas start — that is what a heading is — so the
splitter reads those marks instead of guessing.

Each chunk carries its **heading path**, the trail of ancestor headings down to its
own. That is not decoration: it is what makes a citation legible. "ADR-0006 >
Decision" tells a reader which argument they are looking at; an offset does not. It is
also part of what gets embedded, so a section called "Decision" is not stranded
without the name of the thing it decides.

**Long sections still get split, but never mid-paragraph.** A few sections (the
glossary, the status tables) run past what is sensible to embed as one vector — a
long chunk's embedding is an average of everything in it, so one paragraph's meaning
gets diluted by the nine around it. Those are split at paragraph boundaries, and a
table at row boundaries with its header re-attached, so every piece is still something
that can be quoted whole. The heading path is unchanged and a `part` number
distinguishes them.

Code fences are tracked, because a `# comment` on the first line of a shell block is
not a level-1 heading and a splitter that thinks it is will shred the document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ATX headings only (`## Decision`). The corpus has no Setext headings (`Decision`
# underlined with `---`), and treating a `---` rule as a heading marker would turn
# every horizontal rule in the lane docs into a section break.
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")

# A glossary entry: `**Rung** — one of the five fixed positions...`. Markdown has no
# syntax for a definition list, so a heading-based splitter sees `## 3. Glossary` as one
# section and packs twenty-five unrelated definitions into a handful of chunks. The
# embedding of such a chunk is an average of twenty-five topics and is strongly about
# none of them — measured, "what is the cooldown for" ranked the glossary chunk holding
# the actual definition *fifth*, below the threshold, behind three one-line reason
# codes. A definition begins a new chunk, so each term gets a vector of its own; any
# paragraphs or tables that follow it stay attached, which is right, because they are
# that term's explanation.
_DEFINITION = re.compile(r"^\*\*[^*\n]+\*\*\s*[—–-]\s")

# Roughly 450 tokens. Two constraints meet here. Below: a chunk has to be long enough
# to carry an argument, and most ADR sections are 1-3 paragraphs, so almost nothing
# splits. Above: `gemini-embedding-001` takes 2048 input tokens (~8000 characters), so
# this leaves a wide margin, and more importantly a single vector stops meaning
# anything specific once it is averaging a page of prose.
MAX_CHUNK_CHARS = 1800

# Below this a chunk is a section heading with nothing under it — an ADR's `## Status`
# whose body is one word, or a heading immediately followed by a subheading. Dropping
# them is not about noise in the results: an embedding of "Accepted" is a vector for
# the general idea of acceptance and will surface against questions that have nothing
# to do with this document.
MIN_CHUNK_CHARS = 24


@dataclass(frozen=True, slots=True)
class Chunk:
    """One retrievable passage, and enough provenance to cite it.

    `source` is repo-relative and POSIX-separated so the committed `index.json` is
    byte-identical on Windows and Linux — this file is a build artifact that gets
    diffed in review, and a backslash churn would make that unreadable.
    """

    source: str
    heading_path: tuple[str, ...]
    text: str
    #: 0 for a section that fitted in one chunk; 1-based when a long one was split.
    part: int = 0

    @property
    def citation(self) -> str:
        """How this chunk reads back to a human: `ADR-0006 > Decision`.

        Falls back to the source path when a document has text before its first
        heading, which is the only case with an empty path.
        """
        trail = " > ".join(self.heading_path) if self.heading_path else self.source
        if self.part:
            return f"{trail} (part {self.part})"
        return trail

    @property
    def embedding_text(self) -> str:
        """What actually gets embedded: the heading path, then the body.

        The path is prepended rather than dropped because section titles in this
        corpus carry most of the topic signal — a chunk whose body argues about
        `n + z²` is retrievable for "Wilson interval" only if the words "ADR-0002:
        Wilson score interval over the Wald interval" travel with it.
        """
        trail = " > ".join(self.heading_path)
        header = f"{self.source} > {trail}" if trail else self.source
        return f"{header}\n\n{self.text}"

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "heading_path": list(self.heading_path),
            "part": self.part,
            "text": self.text,
        }

    @classmethod
    def from_json(cls, payload: dict) -> Chunk:
        return cls(
            source=payload["source"],
            heading_path=tuple(payload["heading_path"]),
            text=payload["text"],
            part=payload.get("part", 0),
        )


@dataclass(frozen=True, slots=True)
class _Section:
    heading_path: tuple[str, ...]
    lines: list[str]


def chunk_markdown(text: str, *, source: str) -> list[Chunk]:
    """Split one markdown document into chunks, in document order.

    A section owns the text between its own heading and the next heading of *any*
    level; subsections are separate chunks rather than being folded into their parent.
    Folding would put `### Layer detail` inside `## End-to-end flow` and produce one
    120-line chunk whose embedding says nothing in particular.
    """
    chunks: list[Chunk] = []
    for section in _sections(text):
        body = _clean(section.lines)
        if len(body) < MIN_CHUNK_CHARS:
            continue
        pieces = _split_long(body)
        if len(pieces) == 1:
            chunks.append(Chunk(source=source, heading_path=section.heading_path, text=pieces[0]))
            continue
        for number, piece in enumerate(pieces, start=1):
            term = _defined_term(piece)
            chunks.append(
                Chunk(
                    source=source,
                    # A definition names itself, so the citation can say "Glossary >
                    # Cooldown" instead of "Glossary (part 6)". The heading the author
                    # did not write, recovered from the text they did.
                    heading_path=section.heading_path + ((term,) if term else ()),
                    text=piece,
                    part=0 if term else number,
                )
            )
    return chunks


def _defined_term(piece: str) -> str | None:
    """The bold term a glossary entry opens with, if it is one."""
    match = _DEFINITION.match(piece)
    if match is None:
        return None
    return piece[2 : piece.index("**", 2)].strip().strip("`")


def _sections(text: str) -> list[_Section]:
    """Walk the document, maintaining the stack of open headings."""
    sections: list[_Section] = []
    stack: list[tuple[int, str]] = []
    current = _Section(heading_path=(), lines=[])
    in_fence = False
    fence_marker = ""

    for line in text.splitlines():
        fence = _FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, ""
            current.lines.append(line)
            continue

        match = None if in_fence else _HEADING.match(line)
        if match is None:
            current.lines.append(line)
            continue

        sections.append(current)
        level, title = len(match.group(1)), match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        current = _Section(heading_path=tuple(t for _, t in stack), lines=[])

    sections.append(current)
    return sections


def _clean(lines: list[str]) -> str:
    """Join a section's lines, dropping leading/trailing blank lines and `---` rules.

    Horizontal rules are separators for a human reader and pure noise in an embedding.
    """
    kept = [line for line in lines if line.strip() not in {"---", "***", "___"}]
    return "\n".join(kept).strip()


def _split_long(body: str) -> list[str]:
    """Pack a long section into pieces of at most `MAX_CHUNK_CHARS`, greedily.

    Split points are paragraph boundaries, glossary definitions, and inside an
    over-long table, row boundaries. A single paragraph longer than the limit is
    emitted whole rather than cut — an over-long chunk is a worse embedding, but a
    paragraph severed mid-sentence is a worse *quotation*, and quotable reasoning is
    the thing this index exists to supply.

    Runs on every section, not only the over-long ones: a definition starts a new chunk
    regardless of how much room is left, and a section with neither definitions nor
    excess length falls through and comes back as one piece.
    """
    pieces: list[str] = []
    buffer: list[str] = []
    size = 0
    for block in _blocks(body):
        addition = len(block) + (2 if buffer else 0)
        if buffer and (_DEFINITION.match(block) or size + addition > MAX_CHUNK_CHARS):
            pieces.append("\n\n".join(buffer))
            buffer, size = [block], len(block)
            continue
        buffer.append(block)
        size += addition
    if buffer:
        pieces.append("\n\n".join(buffer))
    return pieces


def _blocks(body: str) -> list[str]:
    """Blank-line separated blocks, with over-long tables broken into rows.

    A markdown table has no blank lines in it, so paragraph splitting alone leaves the
    status tables in `docs/CONTEXT.md` as single 4000-character blocks. Splitting them
    per row and re-attaching the header keeps each row independently quotable and
    independently citable, which is exactly what a "what is the status of X" question
    wants back.
    """
    blocks: list[str] = []
    for raw in re.split(r"\n\s*\n", body):
        block = raw.strip("\n")
        if not block.strip():
            continue
        if len(block) <= MAX_CHUNK_CHARS or not _is_table(block):
            blocks.append(block)
            continue
        blocks.extend(_table_rows(block))
    return blocks


def _is_table(block: str) -> bool:
    lines = [line for line in block.splitlines() if line.strip()]
    return len(lines) >= 3 and all(line.lstrip().startswith("|") for line in lines)


def _table_rows(block: str) -> list[str]:
    """One block per body row, each carrying the table's header and separator."""
    lines = [line for line in block.splitlines() if line.strip()]
    header = "\n".join(lines[:2])
    return [f"{header}\n{row}" for row in lines[2:]]


def chunk_file(path: Path, *, root: Path) -> list[Chunk]:
    """Chunk one markdown file, naming it by its repo-relative POSIX path."""
    source = path.resolve().relative_to(root.resolve()).as_posix()
    return chunk_markdown(path.read_text(encoding="utf-8"), source=source)
