"""The index CLI.

    python -m assistant build              # embed what changed, write assistant/index.json
    python -m assistant build --full       # re-embed every chunk, not just the changed ones
    python -m assistant build --dry-run    # chunk and report, call nothing
    python -m assistant check              # is the committed index current? exit 1 if not
    python -m assistant search "why Wilson instead of Wald"

**Building is a deliberate act.** Not on import, not on first search. The reasons are
the ones `python -m governance.record` already gives: a build spends quota, it produces
a committed artifact somebody has to review, and a lazy build puts its network calls in
front of whoever is watching. `check` is the cheap half — no network, no key — and is
what belongs in CI.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

from assistant.embed import build_embedder
from assistant.index import (
    DEFAULT_INDEX_PATH,
    RELEVANCE_THRESHOLD,
    Index,
    build_chunks,
    build_index,
    load_index,
    save_index,
    search,
    stale_sources,
)
from governance.llm.errors import GovernanceLLMError


def _load_dotenv() -> list[str]:
    """Read `.env`, reusing the governance CLI's loader rather than writing a second.

    Imported here rather than at module scope: it is a dev-time convenience, and only
    the command that promises `.env` works should pay for pulling the governance
    package in.
    """
    from governance.record import load_dotenv

    return load_dotenv()


def _cmd_build(args: argparse.Namespace) -> int:
    chunks = build_chunks()
    by_source: dict[str, int] = {}
    for chunk in chunks:
        by_source[chunk.source] = by_source.get(chunk.source, 0) + 1
    for source, count in by_source.items():
        print(f"  {count:4d}  {source}")
    total_chars = sum(len(c.text) for c in chunks)
    print(f"  {len(chunks):4d}  chunks, {total_chars:,} characters")

    if args.dry_run:
        print("\n--dry-run: nothing embedded, nothing written.")
        return 0

    loaded = _load_dotenv()
    if loaded:
        print(f"\nread {', '.join(loaded)} from .env")

    embedder = build_embedder()
    previous = None if args.full else _previous_index(args.out)
    reused = _reuse_count(previous, chunks, embedder)
    if reused:
        print(f"reusing {reused} vectors from the existing index (--full re-embeds everything)")
    print(
        f"embedding {len(chunks) - reused} chunks with {embedder.model} "
        f"at {embedder.dimensions}d ..."
    )
    try:
        index = build_index(embedder=embedder, previous=previous)
    except GovernanceLLMError as exc:
        print(f"\nembedding failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    path = save_index(index, args.out)
    size_kb = path.stat().st_size / 1024
    print(f"wrote {path} — {len(index.chunks)} chunks, {size_kb:,.0f} KB")
    return 0


def _previous_index(out: Path | None) -> Index | None:
    """The committed index, if there is one, so a build can reuse what it paid for.

    Gemini's free embedding quota counts *contents* rather than requests — 1,000 a day,
    about seven full builds — so editing one ADR must not cost 135 embeddings. Loaded
    without the staleness check on purpose: being out of date with the docs is exactly
    the situation a build is fixing, and warning about it here would be noise.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return load_index(out, check_sources=False)
    except (FileNotFoundError, ValueError):
        return None


def _reuse_count(previous: Index | None, chunks: list, embedder) -> int:
    """How many chunks the previous index already covers, for the build's own report."""
    if previous is None:
        return 0
    if (previous.embedding_model, previous.dimensions) != (embedder.model, embedder.dimensions):
        return 0
    known = {chunk.embedding_text for chunk in previous.chunks}
    return sum(1 for chunk in chunks if chunk.embedding_text in known)


def _cmd_check(args: argparse.Namespace) -> int:
    """No network and no key: this is the half that can run in CI."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        index = load_index(args.index, check_sources=False)
    problems = stale_sources(index)
    print(f"{args.index or DEFAULT_INDEX_PATH}: {len(index.chunks)} chunks, ", end="")
    print(f"{index.embedding_model} at {index.dimensions}d, built {index.built_at}")
    if not problems:
        print("index is current with every source it indexes.")
        return 0
    print("\nSTALE — the index no longer matches the documentation:", file=sys.stderr)
    for name, why in problems.items():
        print(f"  {name}: {why}", file=sys.stderr)
    print("\nRebuild with: python -m assistant build", file=sys.stderr)
    return 1


def _cmd_search(args: argparse.Namespace) -> int:
    _load_dotenv()
    index = load_index(args.index)
    try:
        results = search(index, args.query, args.k)
    except GovernanceLLMError as exc:
        print(f"search failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    if not results or not results[0].is_relevant:
        best = f"{results[0].score:.3f}" if results else "n/a"
        print(f"nothing above the {RELEVANCE_THRESHOLD} relevance threshold (best {best}).")
        print("The honest answer to this question is that the docs do not cover it.")
        return 0

    for rank, result in enumerate(results, start=1):
        mark = " " if result.is_relevant else "~"
        print(f"{mark}{rank}. {result.score:.3f}  {result.citation}")
        if args.verbose:
            body = result.chunk.text if args.full else result.chunk.text[:400]
            print("\n" + "\n".join(f"      {line}" for line in body.splitlines()) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m assistant",
        description="Build, check and query the documentation retrieval index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="chunk, embed and write the index")
    build.add_argument(
        "--dry-run",
        action="store_true",
        help="report the chunking and stop — no embedding calls, nothing written",
    )
    build.add_argument("--out", type=Path, default=None, help="where to write the index")
    build.add_argument(
        "--full",
        action="store_true",
        help="re-embed every chunk instead of reusing unchanged ones from the existing index",
    )
    build.set_defaults(func=_cmd_build)

    check = sub.add_parser("check", help="is the committed index current? no network")
    check.add_argument("--index", type=Path, default=None)
    check.set_defaults(func=_cmd_check)

    query = sub.add_parser("search", help="embed a question and show the top chunks")
    query.add_argument("query")
    query.add_argument("-k", type=int, default=5)
    query.add_argument("--index", type=Path, default=None)
    query.add_argument("-v", "--verbose", action="store_true", help="print the chunk text")
    query.add_argument("--full", action="store_true", help="with -v, do not truncate")
    query.set_defaults(func=_cmd_search)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
