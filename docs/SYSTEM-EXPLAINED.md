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

## 6. Every architectural decision, in one line each

Full reasoning, alternatives, and consequences are in `docs/adr/`. This is
the index, not a substitute for reading them.

| ADR | Decision |
|---|---|
| [0001](adr/0001-statistical-evidence-not-llm-judgment.md) | Statistics, not LLM judgment, decide whether autonomy changes — the LLM explains, it never originates the evidence |
| [0002](adr/0002-wilson-score-interval-over-wald.md) | Wilson score interval, not Wald, for every confidence bound — the interval correctly stays below 1.0 even at 100% observed accuracy on a small sample |
| [0003](adr/0003-deterministic-policy-engine-as-enforcement-boundary.md) | A deterministic Policy Engine, not a prompted agent, is the sole thing that enforces a limit |
| [0004](adr/0004-human-approval-required-for-autonomy-increases.md) | Increases need human sign-off; clawbacks don't — the two directions carry asymmetric risk |
| [0005](adr/0005-shared-contracts-as-cross-lane-treaty.md) | One shared package, `shared/`, is the only source of cross-lane types — no lane forks its own version |
| [0006](adr/0006-two-stage-drift-detection-tripwire-then-z-test.md) | Drift detection is two-stage: a cheap accuracy-drop tripwire, then a real two-proportion z-test to confirm before escalating severity |
| [0007](adr/0007-critical-error-weighting-in-score-not-in-accuracy.md) | Critical errors weight the trust score directly; they never distort the accuracy proportion itself |
| [0008](adr/0008-monolith-over-microservices-for-prototype-scope.md) | One monorepo, in-process calls between lanes — not four deployed microservices, for a five-week capstone with a fixed deadline |
| [0009](adr/0009-post-hoc-audit-sampling-as-ground-truth.md) | Post-hoc human review, sampled at a rate that shrinks as an agent climbs the ladder, is the ground-truth mechanism once the simulator's free ground truth isn't available |
| [0010](adr/0010-main-shared-contracts-canonical.md) | `main`'s frozen `shared/` is canonical over an independently-designed alternative built on `origin/ad/simulator-frontend`; the alternative is ported, not merged, not discarded |

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
