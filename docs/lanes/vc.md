# Governance Lane — AI Context Primer

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

The single design rule the whole architecture is built on:

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

## Who owns what

| Lane | Owner | Directory |
|---|---|---|
| Backend & Policy | Varun P. (team lead) | `backend/` |
| Trust & Risk | Utkarsh | `trust/` |
| **Agentic Governance (this lane)** | **Varun C.** | **`governance/`** |
| Simulation & Frontend | Adhya | `simulator/`, `frontend/` |

`shared/` holds cross-lane contracts and belongs to all four. Frozen until
9 September. Do not modify it.

---

## This lane's job

Four LLM-powered agents read the statistical evidence and produce a **written
recommendation with reasoning**, which a human then approves or rejects.

- **Risk Agent** — evaluates financial exposure. What is the blast radius if
  this agent's limit goes to ₹2,500 and it starts making mistakes?
- **Performance Agent** — reads the trust evaluation and characterises the
  trend. Is this improvement real or is it a small-sample artifact?
- **Compliance Agent** — checks the proposal against stated policy constraints
  and flags anything that violates them.
- **Audit Agent** — reviews decision history and audit records for anomalies:
  clustering of errors, suspicious vendor patterns, gaps in the record.
- **Coordinator** — a LangGraph workflow that runs the four, aggregates their
  opinions, and produces one `Recommendation`.

### The most important boundary in the project

**Governance agents recommend. They never enforce.**

- They never mutate a policy.
- They never write to the database.
- They never change an autonomy limit.
- Their output is advisory text plus a structured recommendation object.

After the coordinator aggregates, the backend applies a **hard ceiling in
deterministic code**: whatever the agents propose, the final limit cannot exceed
what the statistical evidence supports. If the LLM hallucinates "raise this to
₹50,000," the code clamps it and logs the discrepancy.

This is the whole architectural claim of the project. A judge will ask "what
happens when your LLM is wrong?" The answer is "nothing, structurally — it
cannot reach the enforcement path." Your lane has to be built so that answer is
literally true, not aspirational. If your AI assistant proposes having an agent
call a policy-update function, refuse it.

### Other hard boundaries

- No writes to PostgreSQL. Read-only inputs arrive as function arguments.
- Do not import backend code. The backend calls you, not the reverse.
- Do not compute statistics. Utkarsh's trust engine is the only source of
  numbers. If you find yourself calculating an accuracy rate, you are in the
  wrong lane. Read it from the `TrustEvaluation` you were handed.

---

## What you receive and what you return

**Input:** a `TrustEvaluation` from `shared/contracts.py`, produced by the trust
engine. It contains everything the agents reason over:

- `trust_score` (0-100), `components` (weighted breakdown with which were
  available)
- `accuracy`, `human_agreement`, `utilization` — each a `ProportionResult` with
  `successes`, `trials`, `point`, `wilson_lower`, `wilson_upper`
- `critical_errors`, `noncritical_errors`, `critical_error_rate`,
  `critical_errors_in_recent_window`
- `drift` — a `DriftResult` with `severity` (NONE/WARNING/CONFIRMED/CRITICAL),
  `recent_accuracy` vs `baseline_accuracy`, `drop_pp`, `z_statistic`, `p_value`,
  `underpowered`
- `current_limit`, `current_rung`, `recommended_limit`, `recommended_rung`,
  `direction` (INCREASE/HOLD/CLAWBACK), `eligible_for_increase`
- `reason_codes` — machine codes explaining the ladder decision
- `state` — probation / active / restricted / suspended

Read `shared/contracts.py` and `shared/reason_codes.py` directly. They are the
authoritative definitions.

**Output:** a `Recommendation`, plus one `AgentOpinion` per agent. **Both
already exist** in `shared/contracts.py` as of the v1.1 freeze (21 Aug) — do
not define your own shape. `Recommendation` carries `direction`,
`proposed_limit`/`proposed_rung`, `rationale`, `opinions: tuple[AgentOpinion,
...]`, `has_dissent`, `confidence`, `governance_mode`, `status`,
`trust_evaluation_ref`, `clamped`/`clamped_from`. `AgentOpinion` carries
`agent_name`, `verdict` (`CONCUR`/`OBJECT`/`ABSTAIN`), `reasoning`,
`concerns`, `confidence`. Read them directly in `shared/contracts.py` rather
than working from this summary — this is exactly the kind of secondhand
description that goes stale; the file itself doesn't.

**Surface disagreement, don't average it away.** If the Risk Agent objects and
the Performance Agent approves, that conflict is the most interesting thing on
the screen for a human reviewer. Preserve it in the output.

---

## Three modes, and why

The governance layer runs in one of three modes, set by `GOVERNANCE_MODE`:

- **`stub`** — no LLM calls at all. Returns canned opinions with plausible text.
  Lets the rest of the team integrate against you immediately, and makes your
  tests fast and free.
- **`cached`** — real Gemini responses, recorded once, replayed from disk. **This
  is the demo default.** Deterministic, instant, and cannot fail in front of a
  panel.
- **`live`** — actual Gemini API calls, behind a flag, with a timeout and an
  automatic fallback to cached.

Design for all three from day one. Retrofitting caching onto a live-only
implementation costs a day you don't have.

The fallback in live mode is a **demo requirement, not polish**. If the network
drops or the API rate-limits mid-presentation, the system must still produce a
recommendation. Being able to kill the wifi on stage and have the demo continue
is a genuinely strong moment.

Cost: use the Gemini free tier via Google AI Studio. Because cached mode is the
default, total live calls across the project will be in the low hundreds. Do not
introduce any paid service.

---

## Deliverables

Full detail and checks in `docs/DEADLINES.md`; this is the summary for your
lane specifically.

### Mon 24 Aug — start `vc/langgraph-skeleton`

Package config, four agent stubs. Just needs to exist as a branch with a
commit by end of day — the full skeleton below is due Wednesday.

### Wed 26 Aug — `vc/langgraph-skeleton` complete

LangGraph workflow with four agent nodes and a coordinator, running in `stub`
mode only. Zero LLM calls. Returns a valid, fully-populated `Recommendation`
from canned data.

Done means: the backend can call your coordinator with a `TrustEvaluation` and
get back a structurally correct `Recommendation`. Nothing downstream is
blocked on you after this date.

### Sun 30 Aug — `vc/prompts-and-cached-mode`

- One prompt file per agent, versioned, in `governance/prompts/`.
- Structured output via Pydantic. Parse and validate every response; never
  trust raw LLM text to be well-formed JSON.
- Cached mode: record real Gemini responses for a set of representative
  `TrustEvaluation` inputs (high trust, low sample, active drift, critical
  error, at max rung) and commit them as fixtures.
- Tests that run entirely in stub and cached mode.

### Thu 3 Sept — `vc/live-mode`

Live Gemini calls behind a flag, with a timeout, retry, and automatic fallback
to cached on any failure. A test that simulates API failure and asserts the
fallback produces a valid recommendation.

---

## How to work

- Branch off `main`. Feature branches live two days maximum.
- PR into `main`. CI must pass. No direct pushes.
- One line in `docs/DECISION_LOG.md` per merged PR.
- Architectural decisions get an ADR in `docs/adr/` **before** the code lands.
  Read ADR-0001 (statistical evidence, not LLM judgment) and ADR-0004 (human
  approval required for increases) first — they define the constraints your lane
  operates under.
- Daily standup by 11:00: done / doing / blocked.
- Never commit an API key. Use `.env`, and confirm `.env` is gitignored.

## You will get the hardest questions

Fair warning: the panel will ask more questions about this lane than any other,
because "AI agents governing AI agents" is the part that sounds either
impressive or circular depending on how well you explain it. Be ready for:

- *Isn't this just an LLM deciding whether to trust another LLM?* No — and the
  answer is the design rule. The LLM contributes reasoning, not authority.
  Evidence comes from statistics, enforcement from deterministic code,
  authorization from a human.
- *What if the LLM hallucinates a recommendation?* The hard ceiling clamps it,
  the discrepancy is logged, and a human still has to approve. Be able to
  demonstrate this, not just assert it.
- *Why four agents instead of one prompt?* Have a real answer. Separation of
  concerns and preserved disagreement are defensible. "It looked better on the
  architecture diagram" is not.
- *What happens if the LLM is unavailable?* Cached fallback, and the system
  remains safe because governance is advisory.

Write your answers down as you build. Don't try to assemble them in the last
week.

## Instructions for the AI assistant reading this

- Do not write code outside `governance/`.
- Do not modify `shared/`.
- Never propose that a governance agent write to a database, mutate a policy,
  or change an autonomy limit. That breaks the project's core architectural
  claim.
- Never propose computing statistics in this lane. Read them from
  `TrustEvaluation`.
- Explain LangGraph concepts as you go; the human needs to defend this design
  to a technical panel.
- Do not introduce any paid API or service.