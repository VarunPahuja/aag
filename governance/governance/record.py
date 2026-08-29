"""Record real Gemini responses for the scenarios the demo replays.

    python -m governance.record --dry-run     # print what would be called, call nothing
    python -m governance.record               # record every missing scenario
    python -m governance.record --force       # re-record, including what already exists

Lives in `governance/` rather than `scripts/` because the lane brief says not to write
code outside this directory, and because it imports the prompt layer it is exercising.

**Why a script rather than recording on first use.** Recording lazily would mean the
first run of a demo makes twenty live calls, at roughly ten requests per minute, in
front of whoever is watching. Recording is a deliberate act with a rate limit attached;
replay is the thing that has to be instant.

**It validates every response before saving it.** A recording that cannot be parsed is
worse than no recording — it turns a clean "nothing recorded" error into a parse failure
at demo time, and the fix requires a network connection you may not have.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator

from governance.agents.base import AGENT_NAMES
from governance.llm.errors import GovernanceLLMError
from governance.llm.gemini import GeminiClient, GeminiConfig
from governance.llm.recording import RecordingStore, build_recording
from governance.prompts.loader import build_prompt
from governance.prompts.schema import OpinionParseError, parse_opinion
from governance.scenarios import SCENARIOS, Scenario


def iter_work(
    store: RecordingStore, *, force: bool
) -> Iterator[tuple[Scenario, str, bool]]:
    """Yield (scenario, agent_name, already_recorded) for every prompt in the matrix."""
    for scenario in SCENARIOS:
        evaluation = scenario.build()
        for agent_name in AGENT_NAMES:
            prompt = build_prompt(agent_name, evaluation)
            recorded = store.has(prompt.cache_key)
            if recorded and not force:
                yield scenario, agent_name, True
                continue
            yield scenario, agent_name, False


def record_all(*, force: bool = False, dry_run: bool = False) -> int:
    """Record every missing scenario/agent pair. Returns a process exit code."""
    store = RecordingStore()
    config = GeminiConfig.from_env()
    client = GeminiClient(config=config)

    pending = [
        (scenario, agent)
        for scenario, agent, already in iter_work(store, force=force)
        if not already
    ]
    skipped = sum(1 for _, _, already in iter_work(store, force=force) if already)

    total_calls = len(pending)
    minutes = total_calls * config.min_interval_s / 60
    print(f"model            : {config.model}")
    print(f"recordings dir   : {store.directory}")
    print(f"already recorded : {skipped}")
    print(f"to record        : {total_calls}")
    print(f"estimated time   : {minutes:.1f} min at {config.min_interval_s:.0f}s spacing")
    print()

    if dry_run:
        for scenario, agent in pending:
            print(f"  would record  {agent:<12} {scenario.name}")
        return 0

    if not total_calls:
        print("Nothing to do. Use --force to re-record.")
        return 0

    if not config.has_key:
        print(
            "GEMINI_API_KEY is empty. Put a Google AI Studio key in .env (gitignored) "
            "and try again. Stub and cached modes do not need one.",
            file=sys.stderr,
        )
        return 2

    failures = 0
    for index, (scenario, agent_name) in enumerate(pending, start=1):
        prompt = build_prompt(agent_name, scenario.build())
        label = f"[{index}/{total_calls}] {agent_name:<12} {scenario.name}"
        try:
            text = client.generate(prompt)
        except GovernanceLLMError as exc:
            failures += 1
            print(f"{label}  FAILED  {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        # Parse before saving. An unparseable recording only reveals itself at demo
        # time, when the network that could fix it may not be there.
        try:
            parse_opinion(text, agent_name)
        except OpinionParseError as exc:
            failures += 1
            print(f"{label}  INVALID  {exc}", file=sys.stderr)
            continue

        path = store.save(build_recording(prompt, text, config.model))
        print(f"{label}  saved  {path.name}")

    print()
    print(f"done: {total_calls - failures} recorded, {failures} failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m governance.record",
        description="Record real Gemini responses for the cached-mode demo.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-record scenarios that already have a recording",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the call plan and exit without touching the network",
    )
    args = parser.parse_args(argv)
    return record_all(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
