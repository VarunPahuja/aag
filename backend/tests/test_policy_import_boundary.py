"""Enforces ADR-0003 (a deterministic Policy Engine is the sole enforcement
boundary) and ADR-0014 (how that boundary is enforced in code, not just by
convention) at import time.

Scans every source file under `app/policy/` for `import`/`from ... import`
statements and fails the build if any names a forbidden module: a database
driver, a network client, an LLM provider SDK, or `os`/`time` (the two
stdlib entry points to environment reads and wall-clock reads). Modeled on
the same "fail loud on a violated boundary" idiom used elsewhere in this
project — `governance/governance/agents/base.py`'s `require_stub_mode`
raises rather than silently degrading when a caller crosses a line the
architecture depends on staying uncrossed; this test does the analogous
thing for an import rather than a runtime call.

`shared.enums` / `shared.constants` are not forbidden: they are pure,
stdlib-only treaty dataclasses/enums with no database, network, or LLM
dependency of their own (see `shared/contracts.py`'s own docstring: "The
Trust Engine must stay importable with nothing but the standard library").
Depending on them does not compromise this module's purity.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

POLICY_DIR = Path(__file__).resolve().parent.parent / "app" / "policy"

# Database drivers, network clients, LLM provider SDKs, plus the two stdlib
# modules that read the environment or the wall clock. Not exhaustive of every
# package that could ever violate the boundary — exhaustive of the ones a
# reasonable implementation would actually reach for.
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
        # network
        "requests",
        "httpx",
        "aiohttp",
        "urllib",
        "urllib3",
        "socket",
        "http",
        # LLM providers
        "openai",
        "anthropic",
        "google",
        "cohere",
        "mistralai",
        "ollama",
        # environment / wall-clock
        "os",
        "time",
    }
)


def _policy_source_files() -> list[Path]:
    return sorted(POLICY_DIR.rglob("*.py"))


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


def test_policy_package_exists_and_has_source_files():
    # A guard against this test silently passing because the directory is
    # empty or was renamed — an empty glob makes every parametrized check
    # below vacuously pass, which would hide a real regression.
    assert POLICY_DIR.is_dir()
    assert _policy_source_files(), f"no .py files found under {POLICY_DIR}"


@pytest.mark.parametrize("path", _policy_source_files(), ids=lambda p: p.name)
def test_policy_module_has_no_forbidden_imports(path: Path):
    source = path.read_text(encoding="utf-8")
    imported = _imported_top_level_modules(source, str(path))
    violations = imported & FORBIDDEN_TOP_LEVEL_MODULES
    assert not violations, (
        f"{path.relative_to(POLICY_DIR.parent.parent)} imports forbidden module(s) "
        f"{sorted(violations)} — the Policy Engine must have no database, network, "
        "LLM, file I/O, environment, or wall-clock dependency (ADR-0003, ADR-0014)."
    )
