# Frontend Lane — AI Context Primer

**Paste this whole file into your AI assistant at the start of a session. It has
everything needed to work on this lane with no other context.**

---

## The project

We are four final-year students building a capstone prototype for Deloitte
USI, due **15 September 2026**. It is called the **Adaptive AI Governance
Platform (Earned Autonomy Engine)**.

The problem: an AI agent that processes invoices should not be handed unlimited
authority on day one. It starts with a small autonomy limit (it may approve
invoices up to ₹500 by itself, anything larger must be escalated to a human).
As it demonstrates reliable performance, backed by enough statistical evidence,
the system can recommend raising that limit to ₹1,000, ₹2,500, ₹5,000, ₹10,000.
A human must approve every increase. If performance degrades, the system detects
it and claws the limit back automatically.

The design rule:

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

## Who owns what

| Lane | Owner | Directory |
|---|---|---|
| Backend & Policy | Varun P. (team lead) | `backend/` |
| Trust & Risk | Utkarsh | `trust/` |
| Agentic Governance | Varun C. | `governance/` |
| Simulator | **Adhya (port)**, then Utkarsh | `simulator/` |
| **Frontend (this lane)** | **Adhya** | **`frontend/`** |

You own both `simulator/` and `frontend/` through the port (below), then hand
`simulator/` to Utkarsh once it's ported and finalised — see
`docs/DEADLINES.md`. The dashboard is what the panel actually touches, and
it's still the thing that needs your full attention once the port is done.

---

## Current state (23 Aug) — read this before anything else

You already have real, working code: `~35,600` lines on
`origin/ad/simulator-frontend` (97 tests green, `tsc`/`npm run build` clean
once `frontend/nexttemp/` is set aside). None of it is wasted. But it was
built against an independently-designed `shared/` — Pydantic models, a
3-tier × category limit table, `AgentDecisionRecord`, lower_snake reason
codes — with zero names in common with `main`'s frozen v1.1 contracts (frozen
dataclasses, the 5-rung `AUTONOMY_LADDER`, `DecisionRecord`, 18 UPPER_SNAKE
reason codes). This happened because the lane briefs and `docs/DEADLINES.md`
were never committed to git before you started, so the real `shared/` was
invisible from a clone of the 17 Aug scaffold. That is on how this project
was run, not on the work itself — see ADR-0010, which is the actual decision
record, don't relitigate it here.

**`main`'s frozen `shared/` wins.** Your job now is `ad/simulator-port`: port
the code onto the real contracts, not merge it as-is and not throw it away.
`docs/audits/2026-08-23-port-feasibility.md` has the file-by-file breakdown —
read it before you touch anything. Short version: vendor pools, the
distribution knobs, the file-based decision cache, the agent protocol, the
CLI, and (the one genuine surprise) your `AutonomyTimeline.tsx` chart and the
whole structural shell (routing, `Providers`, `Sidebar`, the MSW/query-client
plumbing) survive with type renames only. The labeller's and scripted agent's
rule tables, the API client, `mocks/data.ts`, and the ladder-facing
components (`AutonomyLadder`, `AccuracyGauge`, `HorizontalThresholdGauge`,
`ApprovalRow`) need rewriting against the 5-rung ladder and the real
endpoints. The three fixture JSON files, `uv.lock`, and `frontend/nexttemp/`
get discarded and regenerated, not ported.

**`simulator/simulator/agents/llm.py` is cut, not ported.** A simulator agent
calling Gemini directly is the simulator making its own LLM calls outside
`vc/governance` — that's the exact boundary ADR-0001 exists to hold ("LLM
reasons" belongs to one lane only). The scripted agent plus the cached-mode
agent cover everything the demo needs; this is a scope cut with a stated
reason, not an oversight, and it isn't up for relitigating per-branch either.

---

## This lane's job

The dashboard is the product. Everything else in the system is invisible
plumbing until it shows up on your screens. When judges evaluate this project,
they will spend 90% of their attention on what you built.

### Hard boundaries

- Never read PostgreSQL directly. Everything comes through the backend HTTP API.
- Never import Python or backend code.
- No business logic in the frontend. Do not compute a trust score, decide
  eligibility, or apply a policy rule in TypeScript. If a number needs
  calculating, the backend calculates it and you render it. A governance system
  where the UI computes its own version of the truth is a governance system with
  two sources of truth.

---

## How you stay unblocked

The backend publishes an **OpenAPI schema** — a JSON file that describes every
endpoint, its parameters, and its response shape. FastAPI generates it
automatically. It is committed at `backend/openapi.json`.

(OpenAPI is a spec format, nothing to do with OpenAI. It costs nothing.)

From it you generate:
- TypeScript types, so your code breaks at compile time when the backend changes
- MSW (Mock Service Worker) handlers, so every screen renders with realistic
  fake data before the backend has real data

This means **you never wait for the backend**. Build every view against mocks,
then flip to the real API when it's ready. If you are ever blocked on someone
else's code, you have skipped this step.

There is a CI check that fails if `backend/openapi.json` goes stale. If the
backend changes an endpoint, you will find out from a red build, not during
integration week.

---

## Screens to build

**Dashboard** — the landing view. Agents, their current autonomy limits, trust
scores, current state, anything pending approval.

**Agent detail** — the most important screen in the product. For one agent:
- Current autonomy limit and where it sits on the ladder
  (₹500 → ₹1,000 → ₹2,500 → ₹5,000 → ₹10,000)
- Trust score over time
- Accuracy **with its Wilson confidence band drawn**. Not just a point estimate.
  See below, this matters.
- Drift status with recent vs. baseline accuracy
- Decision history, filterable
- Policy version history: every autonomy change, when, who approved it, why

**Approvals** — the human-in-the-loop queue. A pending recommendation shows the
proposed change, the statistical evidence behind it, and each governance agent's
opinion and reasoning. The reviewer approves or rejects, and a reason is
mandatory. Show agent disagreement prominently when it exists — that conflict is
the most useful thing on the screen.

**Audit** — the immutable log. Every event, actor, timestamp, payload. The audit
log is hash-chained, so include a verification indicator.

**Audit review queue** — a sample of autonomously-approved invoices flagged for
post-hoc human review. This is how the system learns whether its automatic
approvals were actually correct. (Contract for this is landing in a `shared/`
update; build the screen against mocks in the meantime.)

**Simulation console** — start a run, watch progress, inject a performance drop.
The trigger for the most dramatic beat in the demo.

---

## The Wilson band is the one chart that must be right

Accuracy is displayed as a point estimate **and** a confidence interval. The
interval is wide when there are few samples and narrows as evidence accumulates.

This is not decoration. The core argument of the project is that autonomy should
be granted on *sufficient evidence*, not just on a good-looking average. An
agent at 100% accuracy over 5 decisions and an agent at 96% over 400 look
similar as point estimates and are completely different as evidence. The band
makes that visible in one glance.

Every `ProportionResult` from the API gives you `point`, `wilson_lower`, and
`wilson_upper`. Render all three. When a judge asks "why should I believe this
agent deserves more autonomy," the answer should be something you can point at
on screen.

Recharts handles this with an `Area` for the band behind a `Line` for the point
estimate. Free, no account needed.

---

## The demo, and what it demands of you

Ten beats, and the dashboard carries almost all of them:

1. Agent starts at ₹500
2. Invoices process
3. Accuracy, sample size, Wilson lower bound, human agreement, risk band appear
4. Governance agents recommend an increase
5. A human approves it
6. Autonomy visibly rises
7. A performance drop is injected
8. Drift is detected
9. Autonomy is clawed back automatically
10. Performance recovers and the system eventually recommends an increase again

Build so that this arc reads clearly on screen. State transitions should be
obvious: when a clawback happens, it should be unmissable, not a number quietly
changing in a table. The autonomy ladder as a step chart over time is probably
your single most valuable visualisation, because it tells the whole story in one
image.

---

## Deliverables

Full detail and checks in `docs/DEADLINES.md`; this is the summary for your
lane specifically.

### Mon 24 Aug — start `ad/simulator-port`
Work out the type mapping from her `shared/` to `main`'s (her enum/dataclass
name → the real one) and post it in the group before writing code. This is
the step that was skipped the first time.

### Thu 27 Aug — simulator ported
`simulator/` running on `main`'s real contracts, fixtures regenerated with
`simulator generate`, the duplicate `wilson_lower_bound` in `runner.py`
deleted and replaced with an import from `trust/`. Done means `pytest
simulator/` is green against `main`'s `shared/`, not her original one.

### Sat 29 Aug — frontend on real types
`frontend/src/types/api.ts` deleted and regenerated from `backend/openapi.json`
(it should exist by then — Varun P.'s 25 Aug deliverable). `frontend/nexttemp/`
removed. `typecheck` script added to `frontend/package.json`. `shadcn/ui`
added — it was never actually installed despite being in the fixed stack.
Done means `npm run typecheck` is clean and no hand-written API types remain.

### Wed 2 Sept — agent detail + approvals on real contracts
Agent detail and approvals views working end to end against the ported types.
The approve/reject flow submits, with a mandatory reason field, and shows
per-agent governance opinions and dissent — not just a status, the actual
disagreement, which the original `ApprovalRow.tsx` had no field for at all.

### Sat 5 Sept — charts
- Trust score over time
- Autonomy ladder as a step chart, on the **5-rung** ladder — not the 3-tier
  one `AutonomyLadder.tsx` currently hardcodes
- Accuracy with the Wilson band
- Drift indicator: recent vs. baseline

Done means the Wilson band is visible and demonstrably narrows as n grows.
`AutonomyTimeline.tsx` is most of this already — see "Current state" above.

### Mon 7 Sept — real API, mocks retired
Wire to the real API, replacing mocks. No MSW in the running app. **Feature
freeze 9 September** — nothing new after that date, only fixes.

---

## How to work

- Branch off `main`. Feature branches live two days maximum.
- PR into `main`. CI must pass. No direct pushes.
- One line in `docs/DECISION_LOG.md` per merged PR.
- Daily standup by 11:00: done / doing / blocked.
- Never modify `shared/` or any other lane's directory.
- Regenerate types whenever `backend/openapi.json` changes. Don't hand-edit
  generated files.

Stack is fixed: Next.js, TypeScript, Tailwind, shadcn/ui, Recharts. All free,
no accounts. Do not add a paid service or a component library that requires a
license.

## Instructions for the AI assistant reading this

- Do not write code outside `frontend/`.
- Do not put business logic in the frontend — no computing trust scores,
  eligibility, or policy decisions in TypeScript.
- Do not hand-write API types; they are generated from `backend/openapi.json`.
- Do not suggest reading the database directly or importing Python code.
- Prefer server components where they fit, but this is a dashboard with a lot of
  interactivity — don't contort the architecture for it.
- Do not introduce any paid service or licensed component library.
- Explain the reasoning behind component structure decisions; the human needs to
  defend the frontend architecture to a technical panel.