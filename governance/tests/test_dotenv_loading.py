"""`.env` loading for the recording CLI.

`record.py`'s own error message tells the reader to put `<PROVIDER>_API_KEY` in `.env`.
Nothing loaded that file, so following the instruction reproduced the error it was
telling you to fix. These tests pin the behaviour the message promises.

The library is deliberately *not* covered here: importing `governance` must never read
a key off disk. `test_library_import_does_not_read_dotenv` is the one asserting that.
"""

from __future__ import annotations

import os

import pytest

from governance.record import load_dotenv


@pytest.fixture
def env_file(tmp_path):
    """Write a `.env` and hand back its path."""

    def write(text: str):
        path = tmp_path / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    return write


@pytest.fixture(autouse=True)
def _restore_environ():
    """Undo anything a test sets, so ordering cannot leak a key between tests."""
    before = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(before)


def test_reads_a_plain_name_value_line(env_file, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    applied = load_dotenv(env_file("GEMINI_API_KEY=abc123\n"))

    assert applied == ["GEMINI_API_KEY"]
    assert os.environ["GEMINI_API_KEY"] == "abc123"


def test_strips_surrounding_quotes(env_file, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    load_dotenv(env_file('GEMINI_API_KEY="quoted-key"\n'))

    assert os.environ["GEMINI_API_KEY"] == "quoted-key"


def test_skips_comments_and_blank_lines(env_file, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    applied = load_dotenv(
        env_file("# a comment\n\nGEMINI_API_KEY=real\n   \n# GEMINI_MODEL=commented-out\n")
    )

    assert applied == ["GEMINI_API_KEY"]
    assert "GEMINI_MODEL" not in os.environ


def test_an_empty_value_leaves_the_name_unset(env_file, monkeypatch):
    """The state this lane was actually in: `GEMINI_API_KEY=` with nothing after it.

    Setting it to "" would send a keyless request and surface whatever Gemini says
    about it. Leaving it unset makes record.py print "No API key for: gemini", which is
    the true diagnosis and costs no quota.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    applied = load_dotenv(env_file("GEMINI_API_KEY=\n"))

    assert applied == []
    assert "GEMINI_API_KEY" not in os.environ


def test_the_real_environment_wins_over_the_file(env_file, monkeypatch):
    """`GEMINI_API_KEY=x python -m governance.record` must not be overridden.

    A recording is evidence about which key answered. A stale file quietly winning
    would make that evidence wrong.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "from-the-shell")

    applied = load_dotenv(env_file("GEMINI_API_KEY=from-the-file\n"))

    assert applied == []
    assert os.environ["GEMINI_API_KEY"] == "from-the-shell"


def test_a_missing_file_is_not_an_error(tmp_path):
    assert load_dotenv(tmp_path / "nope.env") == []


def test_library_import_does_not_read_dotenv(env_file, monkeypatch):
    """Importing the lane must never pick up a key as a side effect.

    `GeminiConfig.from_env()` reads `os.environ` and nothing else. If someone later
    adds a `load_dotenv()` call to the library, this fails — which is the point.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    env_file("GEMINI_API_KEY=should-not-be-read\n")
    monkeypatch.chdir(env_file("GEMINI_API_KEY=should-not-be-read\n").parent)

    from governance.llm.gemini import GeminiConfig

    assert GeminiConfig.from_env().api_key == ""
