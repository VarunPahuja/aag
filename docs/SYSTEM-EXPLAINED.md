# System Explained

The full design, glossary, and every architectural decision, in one place.
`docs/CONTEXT.md` is the front door — short, kept current, the thing you read
first. This is the long-form reference behind it: read it before the mentor
meeting, before the final Q&A, or any time "why does it work this way"
needs a real answer instead of a one-line summary.

Everything here is checked against the repo as of **2026-08-23**. Due date
**15 September 2026**, feature freeze **9 September 2026**.

---

## 1. The problem, in full

An AI agent approves or rejects invoices. That's a task where a wrong
`APPROVE` moves real money out the door and a wrong `REJECT` merely annoys
someone — the two failure directions are not symmetric, and the whole system
is built around that asymmetry, not around raw accuracy.

Two bad starting points, both obviously wrong once stated:

- **Unlimited authority on day one.** Handing a brand-new, unvalidated agent
  the ability to approve anything is the failure mode every finance
  department already knows to fear, whether the approver is a person or a
  model.
- **A permanent, unmovable cap.** If a genuinely reliable agent is stuck
  approving nothing over ₹500 forever, the system has bought safety by
  making itself useless. Nobody actually wants that either — it's not a
  governance system at that point, it's a rate limiter with extra steps.

The answer this project argues for: **autonomy is earned, incrementally, on
evidence, and can be taken back automatically.** The agent starts at the
floor. Every decision it makes becomes data. When there's enough data, and
the data is good enough, the system can recommend moving the agent one step
up a fixed ladder. A human has to say yes. If the agent's performance later
degrades, the system notices and drops it back down — no human needed for
that direction, because taking away authority is the safe failure mode and
granting it is the dangerous one (ADR-0004).

## 2. The one sentence that decides every disagreement

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

Four different kinds of authority, deliberately never allowed to blur into
each other (ADR-0001):

| Word | Means | Lives in |
|---|---|---|
| **Reasons** | Reads the evidence, writes a human-readable explanation and a recommendation. Cannot act on its own conclusion. | `governance/` |
| **Provide evidence** | Pure arithmetic over the decision log — Wilson bounds, drift tests, a composed score. No LLM call, no judgment call, reproducible by anyone re-running the same function on the same inputs. | `trust/` |
| **Enforces** | The only code that actually changes a spending limit or blocks a decision. Deterministic. Not a prompted model. | `backend/app/policy/` |
| **Authorize** | A human's click, required before autonomy *increases*, not required before it's taken away. | Approvals UI + `POST /recommendations/{id}/approve` |

If you're ever unsure which lane a piece of logic belongs in, ask which of
these four words describes what it's doing. If the honest answer is "it's
reasoning about whether to trust the agent," it belongs in `governance/`,
not `trust/`. If it's "computing a number," it belongs in `trust/`, not
`governance/`. If it's "actually changing what the agent is allowed to do,"
it belongs in `backend/app/policy/` and nowhere else, full stop.

## 3. Glossary

**Rung** — one of the 5 fixed positions on the autonomy ladder: 0 through 4,
corresponding to ₹500, ₹1,000, ₹2,500, ₹5,000, ₹10,000
(`AUTONOMY_LADDER`, `shared/constants.py`). `rung_of(limit)` and
`limit_of(rung)` convert between the two representations; the invariant
`rung_of(current_limit) == current_rung` must always hold on a
`TrustEvaluation`.

**Wilson lower bound** — the low end of a Wilson score confidence interval
on a proportion (ADR-0002), used instead of the raw point estimate wherever
the system decides something. 10/10 correct decisions and 400/416 correct
decisions can look similar as raw accuracy (100% vs. 96%) and are wildly
different as *evidence* — the Wilson lower bound is what makes that
difference visible in a single number, because it accounts for sample size,
not just the ratio.

Computed with `trust/trust_engine/stats/wilson.py`:

| Record | Point accuracy | Wilson lower bound |
|---|---|---|
| 5 / 5 | 100% | ~56.6% |
| 10 / 10 | 100% | ~72.2% |
| 384 / 400 | 96% | ~93.6% |

The agent with a perfect 5-for-5 record scores *worse* than the agent at 96%
over 400, because the lower bound rewards being good **and** having proven
it. That is what "earned" means, mathematically.

**Critical error** — the agent `APPROVE`d an invoice whose ground truth was
`REJECT`. Money left the building. The reverse (wrongly `REJECT`ing a good
invoice) is an error but explicitly *not* a critical one — it costs friction,
not money (`CRITICAL_ERROR_DEFINITION`, `shared/constants.py`; ADR-0007).
Critical errors are weighted into the trust *score*, never folded into the
accuracy proportion itself, so a single critical error can tank trust without
silently corrupting the accuracy number everything else is computed from.

**Drift** — a detected, statistically-supported drop in recent accuracy
versus historical baseline (ADR-0006). Two-stage: a cheap tripwire (has
accuracy dropped more than `DRIFT_ACCURACY_DROP_PP` percentage points?) has
to fire before the system bothers running a real two-proportion z-test to
confirm it. `WARNING` means the tripwire fired but the sample is too small to
confirm statistically; `CONFIRMED` means the z-test backs it up; `CRITICAL`
skips both stages entirely — a single critical error in the recent window is
an immediate, unconditional signal, no statistics required.

**Trust score** — a single 0-100 number composed from four weighted
components (Wilson-bound accuracy, human agreement, the critical-error
penalty, utilization), with weights that redistribute proportionally when a
component has no evidence yet rather than silently scoring "no data" as
zero-risk (`trust/trust_engine/score.py`).

**Cooldown** — the minimum number of decisions that must elapse between
autonomy increases (`COOLDOWN_BETWEEN_INCREASES`), so a lucky streak right
after promotion can't immediately trigger another one. Separate from
**clawback recovery** (`CLEAN_DECISIONS_AFTER_CLAWBACK`), which is the clean
streak required *after* a clawback before the agent is eligible to climb
again.

**`TrustEvaluation`** — the trust engine's complete output contract
(`shared/contracts.py`): every proportion, the drift result, the composed
score, the ladder position, and the reason codes that explain it. The only
thing `governance/` and `backend/` are meant to read to know "how is this
agent doing."

**`Recommendation`** — governance's complete output (v1.1): a proposed
direction and limit, a rationale, one `AgentOpinion` per agent with its own
verdict, and a `has_dissent` flag. Advisory only — see §2. `clamped` /
`clamped_from` record when the backend's hard ceiling reduced what governance
proposed, because the ceiling always wins regardless of what an LLM asked
for.

**Reason code** — one of 18 machine-readable constants
(`shared/reason_codes.py`) that every ladder decision, and every audit-sample
finding, must be explainable through. The rule: the human-readable sentence
is generated *from* a code via `describe()`, never written free-hand — so
"why did this happen" always traces back to a specific, testable code path,
not a paraphrase someone typed once and never re-verified.

**`AuditSample`** — a decision pulled for post-hoc human review at a rate
that shrinks as an agent climbs the ladder (`SAMPLING_RATE_BY_RUNG`, ADR-0009):
100% reviewed at the floor rung, 5% at the top. This is the actual "ROI" of
earned autonomy — not just a bigger ceiling, but less oversight burden to
sustain it — and it's also the ground-truth source once the system runs
against real invoices, where (unlike the simulator) nothing hands the trust
engine a deterministic correct answer for free.

**Hard ceiling / clamp** — deterministic code in the backend that reduces
whatever limit governance proposes down to what the statistical evidence
actually supports, and logs the discrepancy when it does. This is the literal
answer to "what happens if the LLM hallucinates a recommendation" — nothing,
structurally, because the clamp sits between the recommendation and anything
that could act on it.

## 4. The lanes

| Lane | Owner | Directory | Hard rules |
|---|---|---|---|
| Backend & Policy | Varun P. (lead) | `backend/` | Policy Engine module: no DB, no network, no LLM. Pure functions only |
| Trust Engine | Utkarsh | `trust/` | No FastAPI, no SQLAlchemy/psycopg, no Redis/Celery, no network calls, no wall-clock reads, no global mutable state |
| Governance | Varun C. | `governance/` | No DB writes, no policy mutation, no autonomy changes — advisory output only |
| Simulator | Adhya (porting), then Utkarsh | `simulator/` | Never imports backend code or touches the database — talks to the backend only over HTTP |
| Frontend | Adhya | `frontend/` | No business logic — no trust score, eligibility, or policy computation in TypeScript. No hand-edited generated types |

`shared/` belongs to all four and is governed as a treaty (ADR-0005): any
change needs all four reviewers, no exceptions, no matter how small the diff
looks.

## 5. End-to-end flow (intended — see §7 for what's actually wired up)

1. **Simulator** generates a synthetic invoice with a deterministic ground
   truth.
2. The governed agent decides `APPROVE`/`REJECT`/`ESCALATE`, constrained by
   its current limit, which the **Policy Engine** enforces before the
   decision stands.
3. The decision becomes a `DecisionRecord` — simulator's output, trust
   engine's input.
4. Escalated decisions go to a human reviewer, whose ruling fills in
   `recommended_action`/`human_ruling`.
5. **Trust Engine** consumes the decision history plus the agent's current
   standing (`AgentContext`) and produces a `TrustEvaluation`.
6. **Governance** reads the `TrustEvaluation` and produces a `Recommendation`
   with reasoning and per-agent opinions — never grants or revokes anything
   itself.
7. **Policy Engine** applies it: an increase needs a human's approval; a
   clawback (confirmed drift or a critical error) applies automatically.
8. **Dashboard** visualizes all of it — trust score, ladder position, drift
   status, the decision and audit trail.

Read that list once more and notice: the LLM (step 6) sits in the middle,
with deterministic code on both sides of it — the Policy Engine enforcing
before it (step 2) and the hard ceiling clamping after it (step 7). That
placement is the design. It's also the fastest way to answer "what happens
if the LLM is unavailable or wrong": nothing structurally changes, because
neither side of it depends on it being right.

### Layer detail — plain, then technical

The numbered flow above is the summary. This is each step again, slower:
first in plain language, then with the implementation detail a panel might
actually ask about.

**1 — The agent and the invoice**

*Plain:* An invoice arrives. An AI agent looks at it and says approve,
reject, or "I'm not allowed to decide this, send it to a human."

*Technical:* A `DecisionRecord` is created: invoice id, amount, the agent's
`Action`, a sequence number, and — in the simulator — the `ground_truth`
action. Records are immutable frozen dataclasses (`shared/contracts.py`).

**2 — The Policy Engine**

*Plain:* A dumb, strict rule-checker. It knows the agent's current limit. If
the invoice is over the limit, the agent isn't allowed to decide it, full
stop. No AI involved — deliberately boring, because boring things don't
surprise you.

*Technical:* A pure Python module (`backend/app/policy/`), no database,
network, or LLM imports. Roughly `(invoice, policy_version) -> (allowed |
escalate, reason_code)`. Deterministic: identical inputs always produce
identical output. The only code path in the system that determines whether
an action is permitted (ADR-0003).

**3 — The Trust Engine**

*Plain:* The maths. It looks at everything the agent has done and answers
two questions: how good is it, and *how sure are we*. The second question is
what makes this project interesting.

*Technical:* A pure statistical library in `trust/` — no FastAPI, no
database, no network, no clock reads. Takes `DecisionRecord`s plus an
`AgentContext`, returns a `TrustEvaluation`: accuracy/utilization/human
agreement as `ProportionResult`s with Wilson bounds, a two-stage drift
result, a weighted trust score, and the ladder recommendation.

**4 — The governance agents**

*Plain:* Four AI agents read the numbers and write an opinion in English —
risk, performance, compliance, audit. They can disagree, and a coordinator
collects their opinions into one recommendation with reasoning a human can
actually read. They cannot change anything.

*Technical:* A LangGraph workflow in `governance/` — four nodes plus an
aggregator, structured output validated through Pydantic, running in
`stub`/`cached`/`live` mode. Output is a `Recommendation`:
`proposed_limit`, `rationale`, per-agent `AgentOpinion`s, `has_dissent`. Hard
rule: no database writes, no policy mutation, no enforcement — advisory
only. That boundary *should* be enforced by an automated import check
(nothing under `governance/` may import `sqlalchemy`, `psycopg`, `fastapi`,
or `backend.*`), the same way `trust/`'s boundary already is checked by
hand in the state audits; as of 23 Aug `governance/` has no code yet, so
there's nothing to enforce against and no such CI check exists yet either —
worth having before the lane fills in, not after.

**5 — The hard ceiling**

*Plain:* After the AI agents make their recommendation, plain code checks it
against what the statistics actually support. If the AI proposed something
the evidence doesn't back, the code cuts it down and records that it did.

*Technical:* A deterministic clamp applied in the backend after aggregation.
`Recommendation.clamped` and `clamped_from` make the intervention visible in
the API and the audit log rather than hiding it. This is the structural
answer to "what if the LLM is wrong" — not "we prompt it carefully," but "it
cannot exceed the evidence, and when it tries, we log it."

**6 — Human authorization**

*Plain:* A person looks at the recommendation, sees the numbers and the AI's
reasoning, and clicks approve or reject with a written reason. Only then
does the limit change.

*Technical:* An approval creates a new immutable `policy_versions` row.
`agents.current_limit` is never updated without a `policy_versions` row
written in the same transaction — this append-only design is what makes
"what was this agent allowed to do at 14:00 on 3 September" answerable
exactly, rather than a question about a mutated column with no history.
Every decision references the policy version in force when it was made.
Deliberately asymmetric with clawback (ADR-0004): increases need this
step, clawbacks don't, because taking authority away is always the safe
direction to fail in.

**7 — Audit**

*Plain:* Everything that happens gets written down in a log nobody can
quietly edit.

*Technical:* Append-only `audit_log`, hash-chained. Each row stores
`sha256(prev_hash + canonical_json(payload))`. Change any historical row and
every subsequent hash breaks. Cheap to implement, and it turns "immutable
audit records" from a claim on a slide into a property demonstrable live in
about ten seconds.

**8 — Audit sampling**

*Plain:* In a real deployment nobody finds out whether an auto-approved
invoice was actually correct unless someone checks it. So the system
randomly pulls some of them for a human to review afterward — the more the
agent has earned trust, the fewer get checked.

*Technical:* `AuditSample` (`shared/contracts.py`).
`SAMPLING_RATE_BY_RUNG = (1.0, 0.50, 0.25, 0.10, 0.05)` — every decision
reviewed at the floor rung, 5% at the top (ADR-0009). Sampled reviews become
the ground-truth source for accuracy once the system runs past the
simulator, which has no deterministic correct answer to fall back on for a
real invoice.

**9 — The dashboard**

*Plain:* What the judges actually see and touch.

*Technical:* Next.js + TypeScript + Tailwind + shadcn/ui + Recharts,
consuming the backend over HTTP only. No business logic, no database
access, no hand-written API types — types and mocks are generated from
`backend/openapi.json`.

## 6. Every architectural decision, in one line each

Full reasoning, alternatives, and consequences are in `docs/adr/`. This is
the index, not a substitute for reading them. "Defend it" is the one- or
two-sentence answer to the hardest question a panel is likely to ask about
that specific decision — a quick-reference, not the full case.

| ADR | Decision | Defend it |
|---|---|---|
| [0001](adr/0001-statistical-evidence-not-llm-judgment.md) | Statistics, not LLM judgment, decide whether autonomy changes — the LLM explains, it never originates the evidence | *"Isn't this just an LLM deciding whether to trust another LLM?"* No — the decision rests on a computable number with a documented formula; run it twice, get the same answer. The LLM contributes an explanation a human can read, not the verdict. |
| [0002](adr/0002-wilson-score-interval-over-wald.md) | Wilson score interval, not Wald, for every confidence bound — the interval correctly stays below 1.0 even at 100% observed accuracy on a small sample | Point at the 5/5 row in the glossary table above: a perfect record on five decisions scores *worse* than 96% over 400, because we're honest about how little the first one proves. |
| [0003](adr/0003-deterministic-policy-engine-as-enforcement-boundary.md) | A deterministic Policy Engine, not a prompted agent, is the sole thing that enforces a limit | *"What if the LLM fails?"* The system stays safe — the enforcement path contains no LLM and no network call. Worst case, no recommendations get generated and autonomy simply stops changing. |
| [0004](adr/0004-human-approval-required-for-autonomy-increases.md) | Increases need human sign-off; clawbacks don't — the two directions carry asymmetric risk | The risk profile is asymmetric, so the controls are asymmetric: removing authority is always safe, granting it is not. Same logic as revoking access immediately but restoring it through a process. |
| [0005](adr/0005-shared-contracts-as-cross-lane-treaty.md) | One shared package, `shared/`, is the only source of cross-lane types — no lane forks its own version | We have first-hand evidence of the cost of not doing this: `trust/trust_engine/score.py`'s local `ScoreResult` duplicates `TrustEvaluation` under different field names, a documented consequence of the contract not being visible early enough — not a person's mistake, and exactly the failure this rule exists to prevent going forward (`docs/audits/`, ADR-0010). |
| [0006](adr/0006-two-stage-drift-detection-tripwire-then-z-test.md) | Drift detection is two-stage: a cheap accuracy-drop tripwire, then a real two-proportion z-test to confirm before escalating severity | The tripwire is a materiality filter; the z-test is the confirmation. We report "underpowered" rather than pretending to certainty we don't have. |
| [0007](adr/0007-critical-error-weighting-in-score-not-in-accuracy.md) | Critical errors weight the trust score directly; they never distort the accuracy proportion itself | Separation of measurement from valuation: accuracy stays an objective count comparable across agents, and the value judgment lives in one visible, tunable constant instead of quietly warping the statistics underneath it. |
| [0008](adr/0008-monolith-over-microservices-for-prototype-scope.md) | One monorepo, in-process calls between lanes — not four deployed microservices, for a capstone with a fixed deadline | The boundaries that matter here are architectural, not network — enforced by import rules and CI checks, which is stronger than a network hop and doesn't cost a week of infrastructure we don't have. Extracting a real service later would be a deployment change, not a rewrite. |
| [0009](adr/0009-post-hoc-audit-sampling-as-ground-truth.md) | Post-hoc human review, sampled at a rate that shrinks as an agent climbs the ladder, is the ground-truth mechanism once the simulator's free ground truth isn't available | The strongest attack on the whole premise: *"in production you don't know the right answer, so what are you measuring?"* Have this ready — and it doubles as the ROI story, since the review burden falls exactly as trust rises. |
| [0010](adr/0010-main-shared-contracts-canonical.md) | `main`'s frozen `shared/` is canonical over an independently-designed alternative built on `origin/ad/simulator-frontend`; the alternative is ported, not merged, not discarded | *"Doesn't having two incompatible designs undermine your 'one source of truth' claim?"* It happened once, it was caught before shipping, and the fix is the same treaty rule (ADR-0005) working as intended — naming one canonical version and a costed plan to reconcile the rest, not litigating it forever. |

## 7. Current status

The authoritative version of this table lives in `docs/CONTEXT.md`'s
"Current status" section — reproduced here in short form so this document
doesn't need cross-referencing to be useful; if the two ever disagree,
`docs/CONTEXT.md` wins and this copy is stale.

| Lane | State as of 2026-08-23 |
|---|---|
| `shared/` | Merged, frozen v1.1. Done. |
| Trust engine | Statistical core done, 113 tests green. Ladder/cooldown/clawback due 26 Aug, on schedule. |
| Backend | Zero lines. 23 Aug OpenAPI deadline missed, rescheduled to 25 Aug. |
| Governance | Zero lines, zero commits since 17 Aug. |
| Simulator + frontend | ~5,900 real lines on `origin/ad/simulator-frontend`, 97 tests green there, built against an incompatible `shared/`. Being ported per ADR-0010, not merged as-is. |

Full detail: `docs/audits/2026-08-23-state-audit.md` and
`docs/audits/2026-08-23-port-feasibility.md`. Schedule: `docs/DEADLINES.md`.
Open risks: `docs/RISKS.md`.
