"""The CLI, exercised by invoking it.

`pytest` covers the modules underneath; a command that crashes on invocation still
shows green without a test that actually calls `main()`. The same reasoning CI already
applies to the simulator's CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant.__main__ import main
from assistant.embed import FakeEmbedder
from assistant.index import build_index

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dry_run_reports_the_chunking_and_calls_nothing(capsys, monkeypatch):
    def explode(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("--dry-run must not build an embedder")

    monkeypatch.setattr("assistant.__main__.build_embedder", explode)
    assert main(["build", "--dry-run"]) == 0

    out = capsys.readouterr().out
    assert "docs/adr/0002-wilson-score-interval-over-wald.md" in out
    assert "shared/reason_codes.py" in out
    assert "nothing embedded, nothing written" in out


def test_check_passes_on_the_committed_index(capsys):
    assert main(["check"]) == 0
    assert "index is current with every source it indexes." in capsys.readouterr().out


def test_check_needs_no_key(monkeypatch, capsys):
    """This is the half that runs in CI, where there is no key and no network."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert main(["check"]) == 0


def test_check_exits_nonzero_on_a_stale_index(tiny_repo: Path, tmp_path: Path, capsys):
    index = build_index(tiny_repo, embedder=FakeEmbedder())
    payload = index.to_json()
    payload["sources"]["docs/CONTEXT.md"] = "0" * 64
    path = tmp_path / "index.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["check", "--index", str(path)]) == 1
    err = capsys.readouterr().err
    assert "STALE" in err
    assert "python -m assistant build" in err


def test_search_prints_ranked_citations(capsys, monkeypatch):
    """The whole point of the heading path: a result reads as a place in a document."""
    recorded = json.loads(
        (Path(__file__).resolve().parent / "query_vectors.json").read_text(encoding="utf-8")
    )
    question = "why do clawbacks not need human approval"

    class Recorded:
        model = recorded["model"]
        dimensions = recorded["dimensions"]

        def embed_query(self, text: str) -> list[float]:
            return recorded["queries"][text]

        def embed_documents(self, texts):  # pragma: no cover
            raise AssertionError("search must not embed documents")

    monkeypatch.setattr("assistant.__main__.build_embedder", lambda **_: Recorded())
    monkeypatch.setattr("assistant.index.build_embedder", lambda **_: Recorded())
    monkeypatch.setattr("assistant.__main__._load_dotenv", list)

    assert main(["search", question, "-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "ADR-0004" in out
    assert out.count("\n") >= 3


def test_search_says_it_has_nothing_rather_than_serving_a_weak_match(capsys, monkeypatch):
    recorded = json.loads(
        (Path(__file__).resolve().parent / "query_vectors.json").read_text(encoding="utf-8")
    )
    question = "how do I bake sourdough bread"

    class Recorded:
        model = recorded["model"]
        dimensions = recorded["dimensions"]

        def embed_query(self, text: str) -> list[float]:
            return recorded["queries"][text]

        def embed_documents(self, texts):  # pragma: no cover
            raise AssertionError("search must not embed documents")

    monkeypatch.setattr("assistant.index.build_embedder", lambda **_: Recorded())
    monkeypatch.setattr("assistant.__main__._load_dotenv", list)

    assert main(["search", question]) == 0
    out = capsys.readouterr().out
    assert "relevance threshold" in out
    assert "do not cover it" in out


def test_no_subcommand_is_an_error_not_a_default_action():
    with pytest.raises(SystemExit) as exit_code:
        main([])
    assert exit_code.value.code != 0
