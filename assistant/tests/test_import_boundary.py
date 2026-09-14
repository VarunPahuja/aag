"""`assistant/` is a library over static files, not a service.

Modelled on `backend/tests/test_policy_import_boundary.py`, and for the same reason
that test exists: ADR-0008 chose in-process packages over deployed services, which
means nothing but discipline stops a package reaching across a line it was designed
not to cross. Discipline is what a reviewer runs out of at 2am on the fourteenth. A
test does not.

What this package may not do:

* **Touch a database.** It answers from a committed file. A retrieval index that reads
  live rows is a different design with a different failure mode, and picking it up by
  accident — "just this one query, to get the agent's current limit" — is how it would
  happen.
* **Import the backend.** The backend calls this lane; this lane never calls back. The
  same direction `governance/` maintains, and for the same reason: a cycle between a
  library and the service that embeds it is not refactorable afterwards.
* **Import a second LLM SDK.** There is one LLM integration in this repository
  (`governance/llm/`) and `assistant/embed.py` goes through it. An `openai` or
  `google.generativeai` import here would be a second one, with its own retries, its
  own key handling, and its own pacer on the same key.
* **Import a vector database.** The whole argument in `assistant/__init__.py` is that
  135 chunks do not need one (ADR-0008; `docker-compose.yml`'s comment on Redis and
  Celery). A `chromadb` import would quietly settle that.

`httpx` is *not* forbidden, unlike in the Policy Engine: embedding a query is a network
call by definition. It is confined to `governance/llm/gemini.py` all the same — see
`test_the_network_call_stays_behind_the_provider_layer`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent

FORBIDDEN_TOP_LEVEL_MODULES: frozenset[str] = frozenset(
    {
        # database
        "sqlalchemy",
        "psycopg",
        "psycopg2",
        "asyncpg",
        "sqlite3",
        "pymongo",
        "redis",
        # the backend, and the web framework it is built on
        "backend",
        "app",
        "fastapi",
        "starlette",
        "uvicorn",
        # a second LLM integration
        "openai",
        "anthropic",
        "google",
        "cohere",
        "mistralai",
        "ollama",
        "langchain",
        "langgraph",
        # a vector database this corpus does not need
        "chromadb",
        "qdrant_client",
        "pinecone",
        "faiss",
        "weaviate",
        "pgvector",
        # a heavyweight numeric stack, for 135 dot products
        "numpy",
        "scipy",
        "sklearn",
        "torch",
        "transformers",
    }
)

# Only `governance/llm/` may open a socket. Everything else in this package is
# arithmetic over a loaded file.
NETWORK_MODULES: frozenset[str] = frozenset({"httpx", "requests", "aiohttp", "socket", "urllib"})


def _source_files() -> list[Path]:
    return sorted(p for p in PACKAGE.rglob("*.py") if "tests" not in p.parts)


def _imported_top_level_modules(source: str, filename: str) -> set[str]:
    tree = ast.parse(source, filename=filename)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            modules.add(node.module.split(".")[0])
    return modules


def test_the_package_has_source_files_to_check():
    # An empty glob makes every parametrized check below vacuously pass, which would
    # hide the regression rather than report it.
    assert PACKAGE.is_dir()
    assert _source_files(), f"no .py files found under {PACKAGE}"


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_module_has_no_forbidden_imports(path: Path):
    imported = _imported_top_level_modules(path.read_text(encoding="utf-8"), str(path))
    violations = imported & FORBIDDEN_TOP_LEVEL_MODULES
    assert not violations, (
        f"assistant/{path.name} imports {sorted(violations)} — this package is a "
        f"library over static files with no database, no backend dependency, one LLM "
        f"integration and no vector store (see this module's docstring)."
    )


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_the_network_call_stays_behind_the_provider_layer(path: Path):
    imported = _imported_top_level_modules(path.read_text(encoding="utf-8"), str(path))
    violations = imported & NETWORK_MODULES
    assert not violations, (
        f"assistant/{path.name} imports {sorted(violations)} — the one network call "
        f"this package makes belongs to governance/llm/gemini.py, which already owns "
        f"the key handling, the pacing and the error translation."
    )


def test_the_only_project_package_it_depends_on_is_governance_and_shared():
    """Named explicitly, so adding a dependency on another lane is a decision somebody
    has to make in this file rather than a line in an import block."""
    project_packages = {"backend", "trust", "trust_engine", "simulator", "governance", "shared"}
    seen: set[str] = set()
    for path in _source_files():
        seen |= _imported_top_level_modules(path.read_text(encoding="utf-8"), str(path))
    assert seen & project_packages == {"governance", "shared"}
