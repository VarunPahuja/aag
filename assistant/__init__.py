"""A retrieval index over this repository's own documentation.

The assistant answers questions about AAGP. Without retrieval it answers them from
whatever the model already believes about "AI governance platforms", which is fluent,
plausible, and not about this system. This package gives it the actual paragraphs to
quote, with a citation that reads back as "ADR-0006, Decision" rather than "chunk 47".

**No vector database, and no new service.** The corpus is roughly three thousand lines
of markdown; a committed `index.json` plus cosine similarity over it is the whole
implementation, and it matches the standing precedent — ADR-0008 chose in-process
library calls over four deployed services, and `docker-compose.yml` says in a comment
that Redis and Celery were cut and need an ADR to come back. Adding Chroma or pgvector
to search 250 chunks would be the same mistake in a new coat.

**What this is not.** No database, no backend import, no network beyond the one
embedding call a build or a query makes. It is a library over static files, the same
shape as `trust/` — see `tests/test_import_boundary.py`, which enforces that rather
than asking a reviewer to remember it.

Layout:

    chunking.py   markdown -> chunks, split on headings
    embed.py      the embedding call, behind governance's existing Gemini client
    index.py      build, save, load, search
    index.json    the committed artifact
    __main__.py   `python -m assistant build | check | search`

The corpus, and what is deliberately left out, is in `index.py`.
"""

from __future__ import annotations

from assistant.chunking import Chunk, chunk_markdown
from assistant.index import (
    RELEVANCE_THRESHOLD,
    Index,
    IndexStaleWarning,
    SearchResult,
    load_index,
    search,
)

__all__ = [
    "RELEVANCE_THRESHOLD",
    "Chunk",
    "Index",
    "IndexStaleWarning",
    "SearchResult",
    "chunk_markdown",
    "load_index",
    "search",
]
