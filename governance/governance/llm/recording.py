"""Recorded model responses, and the rules for replaying one.

Cached mode is the demo default, not live. A recorded response cannot rate-limit, time
out, or get filtered in front of a panel, and killing the wifi mid-presentation is a
better demonstration of the architecture than any slide about it.

**One file per recording, named by cache key.** Not one big JSON blob: a single file is
a readable diff when a prompt is revised, and re-recording one scenario does not rewrite
the other nineteen.

**A miss raises.** The two quiet alternatives are both worse than an error. Falling back
to stub text makes an unrecorded prompt indistinguishable from a working one — the
reasoning simply stops changing, and nobody notices until someone asks why. Matching a
*similar* recording replays an answer to a question that was not asked.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from governance.llm.errors import RecordingMissError
from governance.prompts.loader import Prompt

# governance/governance/llm/recording.py -> governance/recordings/
DEFAULT_RECORDING_DIR = Path(__file__).resolve().parents[2] / "recordings"

SCHEMA_VERSION = "1"

# A cache key is "<agent>.<version>.<model>.<hash>" and every part is generated, but
# this builds a filesystem path, so it is validated rather than trusted. Anything
# outside this alphabet cannot become a path separator or a parent-directory hop.
_SAFE_KEY = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True, slots=True)
class Recording:
    """One real model response, plus enough context to know what produced it.

    `prompt_sha` is the fingerprint of the exact prompt text sent. The cache key already
    covers agent, prompt version, model and evidence, so a mismatch here means something
    changed that the key was supposed to capture and did not — it is a tripwire on the
    keying scheme itself, not a second lookup mechanism.
    """

    cache_key: str
    agent_name: str
    prompt_version: str
    evidence_hash: str
    provider: str
    model: str
    response_text: str
    prompt_sha: str
    recorded_at: str
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "cache_key": self.cache_key,
            "agent_name": self.agent_name,
            "prompt_version": self.prompt_version,
            "evidence_hash": self.evidence_hash,
            "provider": self.provider,
            "model": self.model,
            "prompt_sha": self.prompt_sha,
            "recorded_at": self.recorded_at,
            "response_text": self.response_text,
        }

    @classmethod
    def from_json(cls, payload: dict, *, source: Path) -> Recording:
        missing = sorted(
            {
                "cache_key",
                "agent_name",
                "prompt_version",
                "evidence_hash",
                "provider",
                "model",
                "prompt_sha",
                "recorded_at",
                "response_text",
            }
            - payload.keys()
        )
        if missing:
            raise ValueError(f"{source.name} is missing field(s): {', '.join(missing)}")
        return cls(
            cache_key=payload["cache_key"],
            agent_name=payload["agent_name"],
            prompt_version=payload["prompt_version"],
            evidence_hash=payload["evidence_hash"],
            provider=payload["provider"],
            model=payload["model"],
            response_text=payload["response_text"],
            prompt_sha=payload["prompt_sha"],
            recorded_at=payload["recorded_at"],
            schema_version=payload.get("schema_version", SCHEMA_VERSION),
        )


def cache_key_for(prompt: Prompt, model_slug: str) -> str:
    """The key one recording is stored under: agent, prompt version, model, evidence.

    **The model belongs in the key, and leaving it out was a bug.** `Prompt.cache_key`
    identifies the *question* — agent, prompt version, evidence — and two providers
    asked the same question give different answers. Keyed without the model, a panel
    switched from Gemini to Claude would replay Gemini's recordings and look perfectly
    healthy doing it: same evidence, same agent, plausible reasoning, wrong model. That
    is precisely the class of silent failure the keying scheme exists to prevent.
    """
    agent, version, evidence_hash = prompt.cache_key.split(".", 2)
    return f"{agent}.{version}.{model_slug}.{evidence_hash}"


@dataclass(frozen=True, slots=True)
class RecordingStore:
    """Reads and writes recordings under one directory."""

    directory: Path = DEFAULT_RECORDING_DIR

    def path_for(self, cache_key: str) -> Path:
        if not _SAFE_KEY.match(cache_key):
            raise ValueError(
                f"unsafe cache key {cache_key!r}: expected only letters, digits, dot, "
                f"dash and underscore"
            )
        return self.directory / f"{cache_key}.json"

    def has(self, cache_key: str) -> bool:
        return self.path_for(cache_key).exists()

    def load(self, cache_key: str) -> Recording:
        """Read one recording, or raise `RecordingMissError` naming what is available.

        The error lists the recorded keys for the same agent rather than every file,
        because the common cause of a miss is an edited prompt or changed evidence, and
        seeing the sibling keys makes that obvious at a glance.
        """
        path = self.path_for(cache_key)
        if not path.exists():
            raise RecordingMissError(
                f"no recording for {cache_key!r} in {self.directory}. "
                f"{self._near_miss_hint(cache_key)} "
                f"Record it with: python -m governance.record",
                cache_key=cache_key,
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Recording.from_json(payload, source=path)

    def save(self, recording: Recording) -> Path:
        """Write one recording, creating the directory if this is the first."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(recording.cache_key)
        path.write_text(
            json.dumps(recording.to_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def keys(self) -> list[str]:
        if not self.directory.exists():
            return []
        return sorted(p.stem for p in self.directory.glob("*.json"))

    def _near_miss_hint(self, cache_key: str) -> str:
        agent = cache_key.split(".", 1)[0]
        siblings = [k for k in self.keys() if k.startswith(f"{agent}.")]
        if not siblings:
            return f"Nothing is recorded for the {agent!r} agent yet."
        return (
            f"Recorded for {agent!r}: {', '.join(siblings)}. Keys are "
            f"agent.promptversion.model.evidence — a difference in the last segment "
            f"means the evidence changed, in the third means a different provider or "
            f"model, and in the second means the prompt was revised."
        )


def build_recording(
    prompt: Prompt,
    response_text: str,
    model: str,
    *,
    provider: str,
    model_slug: str,
) -> Recording:
    """Assemble a `Recording` from the prompt and the client that produced it."""
    return Recording(
        cache_key=cache_key_for(prompt, model_slug),
        agent_name=prompt.agent_name,
        prompt_version=prompt.version,
        evidence_hash=prompt.evidence_hash,
        provider=provider,
        model=model,
        response_text=response_text,
        prompt_sha=prompt_fingerprint(prompt),
        recorded_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def prompt_fingerprint(prompt: Prompt) -> str:
    """A hash of the full prompt text, system and user together."""
    digest = hashlib.sha256()
    digest.update(prompt.system.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(prompt.user.encode("utf-8"))
    return digest.hexdigest()[:16]
