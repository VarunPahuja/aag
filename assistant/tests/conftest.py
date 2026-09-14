"""Fixtures for the assistant tests.

Nothing here touches the network. `FakeEmbedder` stands in for every embedding call;
the one place real vectors are needed — proving that a real question retrieves the
right paragraph — uses recorded ones, the same way this project records model
responses rather than calling a model in a test.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """A throwaway repository with the same corpus shape as the real one.

    `shared/reason_codes.py` is copied rather than invented: `reason_code_chunks`
    reads the category comments out of the file and the sentences out of the imported
    module, and a hand-written stub would let those two disagree in a way the real
    repository cannot.
    """
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "shared").mkdir()

    (tmp_path / "docs" / "SYSTEM-EXPLAINED.md").write_text(
        "# System Explained\n\n## Glossary\n\n"
        "**Cooldown** - the minimum number of decisions that must elapse between "
        "autonomy increases, so a lucky streak cannot ratchet a limit upward.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "CONTEXT.md").write_text(
        "# CONTEXT\n\n## The core design rule\n\n"
        "LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans "
        "authorize. Every disagreement about scope is settled by that sentence.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "adr" / "0001-example.md").write_text(
        "# ADR-0001: Statistical evidence, not LLM judgment\n\n## Decision\n\n"
        "The policy engine decides. The panel advises, and nothing it returns can "
        "change a limit on its own.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "adr" / "0000-template.md").write_text(
        "# ADR-NNNN: Title\n\n## Decision\n\n" + "Fill this in. " * 10,
        encoding="utf-8",
    )
    shutil.copyfile(
        REPO_ROOT / "shared" / "reason_codes.py", tmp_path / "shared" / "reason_codes.py"
    )
    return tmp_path
