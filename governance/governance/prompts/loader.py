"""Load versioned prompt files from disk and assemble one agent's full prompt.

**Why prompts are files, not string literals in the agent modules.** A prompt is the
thing under revision most often in this lane, and a diff of `risk.v1.md` against
`risk.v2.md` is readable by a human deciding whether the change was an improvement. A
diff of a triple-quoted string inside a module that also contains logic is not.

**Why the version is in the filename and in the cache key.** Cached mode replays a
recorded Gemini response for a given evidence block. If a prompt is edited and the
recording is not, the demo replays an answer to a question no longer being asked —
silently, and looking perfectly healthy. Keying on `(agent, prompt_version, evidence)`
makes that a cache miss instead of a lie.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from shared.contracts import TrustEvaluation

from governance.prompts.evidence import evidence_fingerprint, render_evidence
from governance.prompts.schema import response_json_schema

PROMPT_DIR = Path(__file__).parent
SHARED_PREAMBLE = "shared"

# Bump when a prompt file's text changes in a way that would change a model's answer.
# Fixtures recorded under an older version stop matching, by design.
PROMPT_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class Prompt:
    """One fully assembled prompt, plus the identity a cache entry is keyed by."""

    agent_name: str
    version: str
    system: str
    user: str
    evidence_hash: str

    @property
    def cache_key(self) -> str:
        return f"{self.agent_name}.{self.version}.{self.evidence_hash}"


@cache
def load_prompt_text(name: str, version: str = PROMPT_VERSION) -> str:
    """Read one prompt file. Cached — these are read once per process and never change.

    A missing file raises rather than falling back to a generic prompt. An agent
    reasoning from the wrong instructions still returns a well-formed opinion, so the
    failure would be invisible in the output and visible only in the quality of the
    argument, which is precisely the kind of bug nobody finds before a demo.
    """
    path = PROMPT_DIR / f"{name}.{version}.md"
    if not path.exists():
        available = sorted(p.name for p in PROMPT_DIR.glob("*.md"))
        raise FileNotFoundError(
            f"no prompt file {path.name} in {PROMPT_DIR} — found: {', '.join(available) or 'none'}"
        )
    return path.read_text(encoding="utf-8").strip()


def build_prompt(
    agent_name: str,
    evaluation: TrustEvaluation,
    version: str = PROMPT_VERSION,
) -> Prompt:
    """Assemble the shared preamble, one agent's brief, the evidence, and the schema.

    The output contract is appended from `response_json_schema()` rather than written
    into each prompt file, so the shape a model is asked for is generated from the same
    Pydantic model that validates its answer.
    """
    system = "\n\n".join(
        [
            load_prompt_text(SHARED_PREAMBLE, version),
            load_prompt_text(agent_name, version),
        ]
    )
    user = "\n\n".join(
        [
            "# Evidence",
            render_evidence(evaluation),
            "# Required output",
            (
                "Reply with a single JSON object and nothing else. It must validate "
                "against this schema:"
            ),
            "```json",
            json.dumps(response_json_schema(), indent=2, sort_keys=True),
            "```",
        ]
    )
    return Prompt(
        agent_name=agent_name,
        version=version,
        system=system,
        user=user,
        evidence_hash=evidence_fingerprint(evaluation),
    )
