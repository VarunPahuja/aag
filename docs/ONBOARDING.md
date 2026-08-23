# Onboarding

Read this fully before you write any code. Ten minutes now saves days later.

## What we're building

An AI agent approves invoices. It starts allowed to approve up to ₹500 by
itself; anything larger it must escalate to a human. As it builds a track
record, the system measures how well it is doing **and how much evidence we
have**, and can recommend raising the limit one step at a time along the ladder
₹500 → ₹1,000 → ₹2,500 → ₹5,000 → ₹10,000. A human approves every increase. If
performance degrades, the system detects it and lowers the limit automatically,
with no human needed.

The rule the whole architecture follows:

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

Full explanation in `docs/SYSTEM-EXPLAINED.md`. Read it before the mentor
meeting and before the final Q&A.

## First-time setup

    git clone https://github.com/VarunPahuja/aag.git aag
    cd aag
    git fetch --all --prune
    git checkout <your-branch>
    cp .env.example .env

Python lanes:

    python -m venv .venv
    .venv\Scripts\activate            # Windows
    source .venv/bin/activate         # macOS / Linux
    pip install -e ./trust[dev]

Frontend:

    cd frontend && npm install && npm run dev

Verify before writing anything:

    pytest trust/ -q                  # expect 112 passed, 1 skipped
    make up                           # database must come up

If either fails, post the **full error text** in the group before starting work.
Do not build on a broken baseline. If it's broken it is almost certainly not
your fault, and we would rather know in five minutes than in five days.

## If you already cloned before 23 August

Your local copy is behind. `shared/`, the infrastructure, and all the docs
landed after the initial scaffold.

    git fetch --all --prune
    git checkout main && git pull
    git checkout <your-branch>
    git rebase main
    git push --force-with-lease

Use `--force-with-lease`, never `--force`. If the rebase conflicts inside
`shared/`, **stop** and post in the group. Do not resolve `shared/` conflicts
alone.

If you have uncommitted work you care about, `git stash` first and
`git stash pop` after. If you're not sure, ask before running anything.

## Folder map

    shared/         Cross-lane contracts. TREATY. All four review any change.
                    Frozen until 9 Sept.
    backend/        Varun P.  FastAPI, DB, policy engine, integration wiring.
    trust/          Utkarsh.  Pure statistical engine. No FastAPI/DB/network.
    simulator/      Adhya (port), then Utkarsh. Invoice generation, degradation.
    governance/     Varun C.  LangGraph agents. Recommendations only, no writes.
    frontend/       Adhya.    Next.js dashboard. Never touches Postgres or Python.
    docs/           Everyone. Read your lane file first.

You may read any folder. You write only in yours. Need a change in someone
else's folder? Message them. Need a change in `shared/`? Stop and raise it with
all four.

## The rule that cost us a week

**`shared/` is the single source of truth for every type in this system.**

If you need a type that isn't there — a decision record, an enum, a reason code
— **do not define your own**. Ask in the group. Someone else has probably
already defined it, and if they haven't, we add it once, together.

This is not a theoretical risk. In week one, ~35,000 lines were built against an
independently-invented version of `shared/` because the lane briefs were never
committed and nobody knew the real contracts existed. The code was good. It
still had to be ported. Ask first; it takes thirty seconds.

## Always branch from a fresh main

Every single time:

    git fetch --all --prune
    git checkout main && git pull
    git checkout -b <your-lane-prefix>/<task-name>

Branch prefixes: `vp/`, `uk/`, `vc/`, `ad/`.

Never branch off your own old branch. Never work directly on `main` or on your
lane branch. Keep each feature branch to about two days of work; if it grows
bigger, split it.

Then push and open a Pull Request against `main`. CI must pass. VP reviews, or
Utkarsh if VP is unavailable.

## Stub-first: nobody waits

Before you have a real implementation, ship the interface:

- backend → OpenAPI with stub endpoints returning fixtures
- trust → committed `TrustEvaluation` fixture JSON
- governance → `GOVERNANCE_MODE=stub` returns canned opinions
- frontend → MSW mocks generated from the OpenAPI schema
- simulator → committed run fixtures

If you are blocked on someone else's code, message the group immediately. Being
blocked means we made a design mistake, not that you should sit idle.

## Daily

- Standup message by **11:00**: Done / Doing / Blocked. Every day, even if the
  answer is "nothing yet."
- One line in `docs/DECISION_LOG.md` per merged PR.
- Any architectural decision gets an ADR in `docs/adr/` **before** the code
  lands.

## Where everything lives

| File | What it is |
|---|---|
| `docs/lanes/<yours>.md` | Your scope, boundaries, and deliverables. **Paste it into your AI at the start of every session.** |
| `docs/DEADLINES.md` | Every date, every check |
| `docs/SYSTEM-EXPLAINED.md` | The full design, glossary, and every architectural decision explained |
| `docs/CONTEXT.md` | Architecture reference |
| `docs/adr/` | Why each decision was made |
| `docs/audits/` | Point-in-time state audits |
| `docs/RISKS.md` | Live risk register |

## Using an AI assistant

Most of us are. That's fine and expected. Two rules:

**Paste your lane file in first, every session.** Without it your AI has no idea
what `shared/` contains, what your boundaries are, or what the other three
people are building. It will confidently generate code that breaks someone
else's lane.

**Your AI does not get to invent contracts.** If it suggests defining a type
that sounds like it belongs in `shared/`, that is the signal to stop and ask
the group.

## Getting help

Post in the group. Say what you tried and paste the actual error text. "It's
not working" is not something anyone can help with.

Being stuck for an hour is normal. Being stuck for a day in silence is the
thing that actually costs us the deadline.