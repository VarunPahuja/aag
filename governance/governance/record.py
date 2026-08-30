"""Record real model responses for the scenarios the demo replays.

    python -m governance.record --dry-run     # print what would be called, call nothing
    python -m governance.record               # record every missing scenario
    python -m governance.record --force       # re-record, including what already exists

Lives in `governance/` rather than `scripts/` because the lane brief says not to write
code outside this directory, and because it imports the prompt layer it is exercising.

**Why a script rather than recording on first use.** Recording lazily would mean the
first run of a demo makes twenty live calls, at roughly ten requests per minute on
Gemini's free tier, in front of whoever is watching. Recording is a deliberate act with
a rate limit attached; replay is the thing that has to be instant.

**Each agent may be on a different provider** (ADR-0012), so the plan is printed before
anything is sent — a panel that is accidentally four Gemini agents costs nothing to fix
beforehand and is invisible afterwards.

**It validates every response before saving it.** A recording that cannot be parsed is
worse than no recording — it turns a clean "nothing recorded" error into a parse failure
at demo time, and the fix requires a network connection you may not have.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator

from governance.agents.base import AGENT_NAMES
from governance.llm.base import LLMClient
from governance.llm.errors import GovernanceLLMError
from governance.llm.recording import RecordingStore, build_recording, cache_key_for
from governance.llm.registry import build_client, describe_panel
from governance.prompts.loader import build_prompt
from governance.prompts.schema import OpinionParseError, parse_opinion
from governance.scenarios import SCENARIOS, Scenario


def iter_work(
    store: RecordingStore, clients: dict[str, LLMClient], *, force: bool
) -> Iterator[tuple[Scenario, str, bool]]:
    """Yield (scenario, agent_name, already_recorded) for every prompt in the matrix."""
    for scenario in SCENARIOS:
        evaluation = scenario.build()
        for agent_name in AGENT_NAMES:
            prompt = build_prompt(agent_name, evaluation)
            key = cache_key_for(prompt, clients[agent_name].slug)
            yield scenario, agent_name, store.has(key) and not force


def _first_agent_on(clients: dict[str, LLMClient], provider: str) -> str:
    """Any agent using this provider — they share one client, so any of them will do."""
    return next(name for name, client in clients.items() if client.provider == provider)


def record_all(*, force: bool = False, dry_run: bool = False) -> int:
    """Record every missing scenario/agent pair. Returns a process exit code."""
    store = RecordingStore()
    clients: dict[str, LLMClient] = {name: build_client(name) for name in AGENT_NAMES}
    panel = describe_panel(AGENT_NAMES)

    pending = [
        (scenario, agent)
        for scenario, agent, already in iter_work(store, clients, force=force)
        if not already
    ]
    skipped = sum(1 for _, _, already in iter_work(store, clients, force=force) if already)

    total_calls = len(pending)
    # Agents on one provider share a client and therefore a pacer, because a rate limit
    # belongs to the key rather than to the agent. So the run is bounded by whichever
    # *provider* has the most calls to make, not by the total and not by any one agent.
    by_provider: dict[str, int] = {}
    for _, agent in pending:
        by_provider[clients[agent].provider] = by_provider.get(clients[agent].provider, 0) + 1
    seconds = max(
        (count * clients[_first_agent_on(clients, p)].config.min_interval_s
         for p, count in by_provider.items()),
        default=0.0,
    )
    minutes = seconds / 60

    print(f"recordings dir   : {store.directory}")
    print("panel            : " + ", ".join(f"{a}={p}" for a, p in panel.items()))
    for name in AGENT_NAMES:
        print(f"  {name:<12} {clients[name].model}  ->  {clients[name].slug}")
    if len(set(panel.values())) == 1:
        print(
            f"  note: all four agents use {next(iter(panel.values()))}. Set "
            f"GOVERNANCE_PROVIDER_<AGENT> to mix providers — a single-model panel shares "
            f"one model's biases (ADR-0012)."
        )
    print(f"already recorded : {skipped}")
    print(f"to record        : {total_calls}")
    print(f"estimated time   : {minutes:.1f} min")
    print()

    if dry_run:
        for scenario, agent in pending:
            print(f"  would record  {agent:<12} {clients[agent].slug:<22} {scenario.name}")
        return 0

    if not total_calls:
        print("Nothing to do. Use --force to re-record.")
        return 0

    missing_keys = sorted({clients[a].provider for _, a in pending if not clients[a].has_key})
    if missing_keys:
        print(
            f"No API key for: {', '.join(missing_keys)}. Set the matching "
            f"<PROVIDER>_API_KEY in .env (gitignored), or point those agents at a "
            f"provider you do have a key for. Stub and cached modes need no key.",
            file=sys.stderr,
        )
        return 2

    failures = 0
    for index, (scenario, agent_name) in enumerate(pending, start=1):
        client = clients[agent_name]
        prompt = build_prompt(agent_name, scenario.build())
        label = f"[{index}/{total_calls}] {agent_name:<12} {client.slug:<22} {scenario.name}"
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

        path = store.save(
            build_recording(
                prompt,
                text,
                client.model,
                provider=client.provider,
                model_slug=client.slug,
            )
        )
        print(f"{label}  saved  {path.name}")

    print()
    print(f"done: {total_calls - failures} recorded, {failures} failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m governance.record",
        description="Record real model responses for the cached-mode demo.",
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
