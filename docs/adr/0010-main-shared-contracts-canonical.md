# ADR-0010: `main`'s frozen `shared/` contracts are canonical; the divergent design is ported, not merged

## Status

Accepted

## Context

Two incompatible definitions of the core domain existed simultaneously.
`main` carried the frozen v1.1 `shared/` contracts (`ad4b58c`, merged
2026-08-21): plain frozen dataclasses, the 5-rung `AUTONOMY_LADDER = (500,
1000, 2500, 5000, 10000)`, `DecisionRecord`, and 18 `UPPER_SNAKE` reason
codes. `origin/ad/simulator-frontend` (`1b1c416`, pushed 2026-08-23)
independently designed its own: Pydantic v2 `BaseModel`s, a 3-tier ×
category `TIER_LIMITS` / `CATEGORY_LIMIT_OVERRIDES` table, `AgentDecisionRecord`,
and 13 `lower_snake` reason codes — with zero names in common with `main`'s
version — and built roughly 35,600 lines on top of it (of which around 5,900
are real authored code once generated fixture JSON is excluded; see
`docs/audits/2026-08-23-port-feasibility.md`).

The root cause is a coordination failure by the team lead, not a lapse by the
branch's author. The lane briefs (`docs/lanes/*.md`) and the deadline sheet
(`docs/DEADLINES.md`) were never committed to git — they existed only outside
version control until 2026-08-23. Anyone who cloned the repo from the 17 Aug
scaffold commit had no way to discover that a `shared/` v1.1 even existed, let
alone what shape it was. Building a self-consistent, well-tested invoice
governance system from that starting point — which is what happened — was a
reasonable thing to do with the information available. The information
available was the problem.

## Decision

**`main`'s frozen v1.1 `shared/` contracts are canonical.** The divergent
design on `origin/ad/simulator-frontend` is **partially ported, not merged
and not discarded.**

This is not a judgment that the 3-tier model was a worse idea in isolation —
`docs/audits/2026-08-23-port-feasibility.md` calls out
`CATEGORY_LIMIT_OVERRIDES` specifically as a genuinely good idea (see
Consequences). It is a statement that only one definition of the domain can
exist in a governance system whose entire architectural claim rests on there
being a single source of truth (ADR-0005), and `main`'s version is the one
the rest of the system — the trust engine, eight prior ADRs, 113 passing
tests — is already built on.

## Consequences

**Scope is smaller than the raw line count suggests.** Per
`docs/audits/2026-08-23-port-feasibility.md`, the ~35,600 lines on the branch
break down as: 13,780 lines DISCARD (dominated by 12,743 lines of generated
fixture JSON — cheap to regenerate, not worth porting as data), 1,142 lines
RENAME (type names change, logic doesn't), 686 lines LOCAL (no dependency on
`shared/` at all, ports untouched), and 4,100 lines REWRITE. The real code in
play is closer to **5,900 lines**, not 35,600.

**What transfers close to free (RENAME + LOCAL, ~1,828 lines):** the invoice
generator's vendor/employee/date pools and log-normal amount distribution
(`simulator/simulator/distributions.py`, `generator.py`'s non-boundary
logic), the file-based decision cache (`agents/cache.py`), the agent protocol
(`agents/base.py`), the CLI (`cli.py`), and — the one genuine surprise on the
frontend side — `AutonomyTimeline.tsx` and the entire structural shell
(routing, `Providers`, `Sidebar`, the MSW/query-client plumbing). None of
that code assumed a 3-tier scale in the first place.

**What needs rewriting (REWRITE, ~4,100 lines):** the labeller's and scripted
agent's rule tables (`simulator/simulator/labeller.py`,
`agents/scripted.py`), both keyed directly to `TIER_LIMITS` /
`CATEGORY_LIMIT_OVERRIDES` and needing to collapse onto the single-axis
5-rung ladder instead; the ladder-facing frontend components
(`AutonomyLadder.tsx` hardcodes 3 tiers at ₹3,000/₹15,000/₹50,000 directly;
`HorizontalThresholdGauge.tsx`'s single 0.85-threshold model doesn't
represent the real 6-condition eligibility gate); and the API client layer
(`api_client.ts`/`mocks/handlers.ts`/`types/api.ts`), where only 1 of 8
endpoint groups (`simulationApi`) matches the real backend surface in
`docs/lanes/vp.md`. **Stated plainly: the API client would need writing
against the real backend under any decision** — porting it, rebuilding it, or
never having diverged in the first place all cost roughly the same here, so
this piece is not a cost attributable to the divergence.

**What's dropped outright:** `simulator/simulator/agents/llm.py`, the agent
that called Gemini directly from inside the simulator. A simulator agent
making its own LLM calls is the simulator reaching into the one authority
ADR-0001 reserves for `vc/governance` — "LLM reasons" is a lane, not a
capability every part of the system gets to use. This is a scope cut with a
stated architectural reason, not an oversight: the scripted agent and the
cached-mode agent between them cover what the demo needs, and nothing about
the ten-beat demo arc requires the invoice-approving agent itself to be a
live LLM call.

**The duplicate Wilson implementation is deleted.** `runner.py:56` defines
its own `wilson_lower_bound()`, computed identically to
`trust/trust_engine/stats/wilson.py`'s version but over a flat whole-run
window rather than the trust engine's recent-vs-baseline split. Post-port,
`runner.py` imports `trust`'s implementation instead. Exactly one
implementation of the Wilson score interval exists in this repository.

**Estimated cost: 7-9 person-days to port, versus 10-13 to discard and
rebuild from scratch using the divergent code purely as a reference**
(`docs/audits/2026-08-23-port-feasibility.md`). Porting is cheaper, mainly
because of the ~1,828 lines that transfer with near-zero effort — a
from-scratch rebuild would have to re-author all of that too, even while
visually copying the same structure.

**`CATEGORY_LIMIT_OVERRIDES` — a genuinely good idea, recorded as future
work, not built now.** Tightening the effective limit per invoice category
(travel vs. supplies vs. consulting) on top of the rung an agent has earned
is a real refinement the frozen design doesn't currently have — the ladder is
a single scalar with no category dimension. It is explicitly out of scope for
this port: introducing it now would mean re-opening `shared/` mid-freeze for
a feature nothing currently demands, on a schedule that has no slack for it.
If the team wants category-aware limits after 15 September, it gets its own
ADR and its own `shared/` PR with all four reviewers, the same as any other
treaty change (ADR-0005) — not smuggled in as part of a port.

## Alternatives considered

- **Adopt the 3-tier model as canonical instead.** Rejected. The 5-rung
  autonomy ladder is not an implementation detail of the trust engine — it
  *is* the product concept the whole capstone argument rests on ("earned
  autonomy," one step at a time, human-authorized). `trust/`'s 113 tests are
  written against `rung_of()`/`limit_of()` and the 5-value `AUTONOMY_LADDER`
  directly. Eight ADRs (0001-0009) reference or depend on this shape. Adopting
  the alternative model would mean rewriting the trust engine, not the
  simulator — a strictly larger, riskier change for no offsetting benefit.
- **Maintain both models behind an adapter/translation layer at the
  boundary.** Rejected. This is the literal failure mode ADR-0005 exists to
  prevent: "a schema-first approach... would still need the same
  four-reviewer discipline on the schema files themselves," and an adapter
  layer is exactly a second source of truth with a translation step bolted
  on, not a removal of one. A governance system whose core sales pitch is
  "one auditable definition of what happened" cannot itself run on two
  definitions of what an invoice decision is.
- **Discard the divergent branch and rebuild the simulator and frontend from
  nothing.** Rejected on the port-feasibility probe's own numbers: 10-13
  person-days against 7-9 for the port, a 3-4 day gap the schedule cannot
  absorb twice (once for the original build, again for a rebuild). The
  simulator is also a 4 Sept deliverable nobody else has started — discarding
  working, if misdirected, code here is materially more expensive than
  fixing its foundation.
