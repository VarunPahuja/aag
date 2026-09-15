# Presentation Facts — Adaptive AI Governance Platform (AAGP)

Every number below was produced by running a command or reading a file
against `origin/main` @ **`1f14bc1`** (2026-09-15, submission day) — none are
recalled from memory. Where a figure could not be verified, that is stated
rather than estimated. Written to be read aloud from and lifted onto slides
directly.

---

## SCALE AND EFFORT

### Lines of code, per lane, app vs. test

Counted with `find <dir> -name '*.py' ... | xargs wc -l` (Python lanes) and
the `.ts`/`.tsx` equivalent for `frontend/src`, excluding `__pycache__`,
`.hypothesis`, and `node_modules`.

| Lane | App code | Test code | Total |
|---|---:|---:|---:|
| `backend/` | 7,510 | 6,291 | 13,801 |
| `governance/` | 4,109 | 2,544 | 6,653 |
| `frontend/src/` (`.ts`/`.tsx`) | 8,456 | — (no separate test tree found) | 8,456 |
| `simulator/` | 2,146 | 1,960 | 4,106 |
| `assistant/` | 1,366 | 1,418 | 2,784 |
| `trust/` | 743 | 1,264 | 2,007 |
| `shared/` | 482 | — (tested from within each lane) | 482 |
| **Total** | **24,812** | **13,477** | **≈38,289** |

*Source: `find <lane> -name "*.py" -not -path "*/tests/*" | xargs wc -l` (app)
and the `tests/` equivalent, run directly against `origin/main` @ `1f14bc1`,
2026-09-15.*

### Test count per lane, and total

| Lane | Pass | Fail | Skip | Total |
|---|---:|---:|---:|---:|
| `trust/` | 174 | 0 | 0 | 174 |
| `governance/` | 251 | 0 | 0 | 251 |
| `backend/` | 327 | 0 | 0 | 327 |
| `simulator/` | 134 | 0 | 0 | 134 |
| `assistant/` | 115 | 0 | 3 | 118 |
| **Total** | **1,001** | **0** | **3** | **1,004** |

*Source: `pytest <lane> -q`, each lane run separately (a combined run from
repo root fails on a `tests.conftest` import-path collision — every lane's
test package is bare `tests`, with no namespacing). Verified twice,
independently, on two separate checkouts, matching exactly both times. The
3 skips are a real, currently-open gap — see `docs/audits/2026-09-14-final-audit.md` §2.*

**Say on stage:** "One thousand and four tests, one thousand and one
passing, across five independently-owned codebases, zero failures."

### PRs, commits, contributors

| Metric | Count | Source |
|---|---:|---|
| Merged PRs | 51 | `gh pr list --state merged --limit 100` |
| Open PRs against `main` | 0 | `gh pr list --state open` |
| Commits on `main` | 79 | `git rev-list --count origin/main` |
| Distinct git author names | 6 (`Varun Pahuja`, `Varun`, `UtkarshSahgal`, `Varun Chaurasia`, `Adhya Sharma`, `radarrot`) | `git shortlog -sn origin/main` — first two names are almost certainly the same person under two git configs (32 + 18 = 50 commits); `radarrot` is unexplained by this audit and not asserted to be anyone in particular |

### ADRs, audits, docs

| Metric | Count | Source |
|---|---:|---|
| ADRs (numbered decisions, excluding the template) | 15 | `ls docs/adr/ \| grep -v template` |
| Audit reports committed to `main` | 5 | `docs/audits/*.md` on `origin/main` (`2026-08-21`, `2026-08-23` ×2, `2026-08-27`, `2026-08-31`) |
| Additional point-in-time audits produced as read-only working sessions, never committed (by the same convention every audit in this series follows) | 4 more (`2026-09-02`, `2026-09-06`, `2026-09-08`, `2026-09-12`) + this pair | Present in the working checkout, not on `origin/main` — say "nine audits across the project" only with this caveat attached |
| Total markdown files under `docs/` | 34 | `find docs -name "*.md" \| wc -l` |

### Project duration

**29 days.** First commit `c126543`, 2026-08-17 23:56:58 IST
(`git log --reverse --format=%ci origin/main \| head -1`) to submission,
2026-09-15.

### Database tables, API endpoints, reason codes

| Metric | Count | Source |
|---|---:|---|
| Database tables | 11 (`agents`, `users`, `decisions`, `invoices`, `policy_versions`, `recommendations`, `trust_evaluations`, `approvals`, `audit_samples`, `audit_log`, `simulation_runs`) | `grep -rn "__tablename__" backend/app/models/` |
| API endpoints | 21 | `grep -rn "@router\.(get\|post\|put\|patch\|delete)" backend/app/api/v1/*.py \| wc -l` |
| Reason codes | 18, of which **17 reachable live** | `shared/reason_codes.py` — the one unreachable code, `SAMPLE_EVIDENCE_INSUFFICIENT`, is only ever imported and checked for in `governance/governance/agents/audit.py:22,34`, never produced anywhere in `trust/` or `backend/`; confirmed by repo-wide grep, unchanged since the 2026-09-12 audit |

---

## THE STATISTICAL ARGUMENT

### The Wilson comparison, computed for real

Run directly against `trust/trust_engine/stats/wilson.py`'s
`wilson_interval()` — not quoted from the glossary, though it matches:

| Record | Point accuracy | Wilson lower bound |
|---|---:|---:|
| 5 / 5 | 100.0% | **56.6%** |
| 10 / 10 | 100.0% | **72.2%** |
| 50 / 50 | 100.0% | **92.9%** |
| 384 / 400 | 96.0% | **93.6%** |
| 950 / 1000 | 95.0% | **93.5%** |

**Say on stage:** "A perfect five-for-five record proves 56.6% — worse than
an agent at 95% over a thousand decisions, which proves 93.5%. That gap is
the entire argument for why we never read the raw number."

*Source: `python -c "from trust_engine.stats.wilson import wilson_interval; print(wilson_interval(5,5))"` etc., run 2026-09-15 against `trust/trust_engine/stats/wilson.py` on `origin/main`.*

### The exact constants

From `trust/trust_engine/constants.py` (lane-local; deliberately not in
`shared/`, so the team can tune without a four-reviewer sign-off):

| Constant | Value |
|---|---|
| `Z_95` (confidence level) | 1.96 |
| `WEIGHT_WILSON_LOWER` | 0.50 |
| `WEIGHT_HUMAN_AGREEMENT` | 0.25 |
| `WEIGHT_CRITICAL_PENALTY` | 0.15 |
| `WEIGHT_UTILIZATION` | 0.10 |
| `MIN_RULED_ESCALATIONS_FOR_AGREEMENT` | 5 |
| `MIN_SAMPLE_FOR_INCREASE` | 30 |
| `MIN_TRUST_SCORE_FOR_INCREASE` | 70.0 |
| `RECENT_WINDOW` | 50 decisions |
| `CRITICAL_ERROR_WINDOW` | 20 decisions |
| `CRITICAL_ERROR_WEIGHT` | 5.0 |
| `DRIFT_ACCURACY_DROP_PP` | 10.0 percentage points |
| `DRIFT_MIN_N_FOR_TEST` | 30 |
| `DRIFT_ALPHA` | 0.05 |
| `COOLDOWN_BETWEEN_INCREASES` | 100 decisions |
| `CLEAN_DECISIONS_AFTER_CLAWBACK` | 75 decisions |

The **six increase gates** (`trust/trust_engine/ladder.py:92-123`):
`INSUFFICIENT_SAMPLE`, `TRUST_BELOW_THRESHOLD`, `AT_MAX_RUNG`,
`DRIFT_ACTIVE` (evidence gates — block `eligible_for_increase`), plus
`COOLDOWN_ACTIVE`, `CLAWBACK_RECOVERY_PENDING` (cooldown gates — block
`direction` only, never eligibility itself — an agent can be
`eligible_for_increase=True` with `direction=HOLD`, a real and meaningful
state, not a bug).

The **two clawback triggers** (`ladder.py:74-86`), checked first,
unconditionally, before any increase logic: `DriftSeverity.CRITICAL` →
`CLAWBACK_CRITICAL_ERROR`; `DriftSeverity.CONFIRMED` → `CLAWBACK_DRIFT`. Both
drop exactly `max(current_rung - 1, 0)` — one rung, never below the floor,
identically for either trigger.

### The five ladder rungs and sampling rate per rung

From `shared/constants.py` (a `shared/` treaty constant — all four lanes
must agree exactly):

| Rung | Limit | Sampling rate (share of decisions reviewed by a human) |
|---|---:|---:|
| 0 (floor) | ₹500 | 100% |
| 1 | ₹1,000 | 50% |
| 2 | ₹2,500 | 25% |
| 3 | ₹5,000 | 10% |
| 4 (ceiling) | ₹10,000 | 5% |

**Say on stage:** "The review burden falls from 100% to 5% as trust rises —
that shrinking oversight cost is the system's ROI, not a side effect."

---

## WHAT THE DEMO ACTUALLY SHOWS

Run twice, live, full reset between runs, `scripts/demo.ps1 -NoPause`
(2026-09-15, against `origin/main`'s merged content). Both runs matched
byte-for-byte after normalizing IDs.

| Beat | What happens | Real numbers (run 1) | Architectural claim it evidences |
|---|---|---|---|
| 1 | Agent-01's starting position | limit ₹2,500, rung 2 | The agent starts mid-ladder on real seed data, not a rigged floor |
| 2 | A simulation run builds fresh evidence, then 6 escalations get ruled | 120 decisions, accuracy 91.4%, Wilson LB 81.4% | Evidence is earned from real decision volume, not asserted |
| 3 | The trust evaluation | accuracy 91.7% (n=60), **Wilson lower bound 81.9%**, trust score 83.1 | ADR-0002: the ladder reads the lower bound, never the point estimate |
| 4 | Governance generates a recommendation | `direction=INCREASE status=PENDING has_dissent=False`, 4/4 agents CONCUR | A live-earned increase, not seed data — governance reasons, it does not decide |
| 5 | A human approves | `status=APPROVED` | ADR-0004: an increase requires a human click |
| 6 | The limit actually moves | **₹2,500 → ₹5,000, rung 2 → 3** | The Policy Engine — deterministic code, not a prompt — is what actually changes authority |
| 7 | A critical error is injected | one `APPROVE` where ground truth is `REJECT` | The one error type that matters: money leaving the building |
| 8 | Drift detection catches it | `drift.severity=CRITICAL`, 1 error in the 20-decision window | ADR-0006: a single critical error is enough for immediate `CRITICAL`, no waiting for a trend |
| 9 | Clawback applies automatically | **before ₹5,000/rung 3 → after ₹2,500/rung 2, zero `/approve` calls** | ADR-0004's asymmetry, made visible: reductions need no human step |
| 10 | The audit chain is verified | `chain_valid=True`, scope `full`, 205 entries | Every entry hash-linked and re-verified live, not merely asserted |

**Total runtime:** 22.2s (run 1), 19.8s (run 2), each including a full
Postgres volume drop, recreate, migrate, and reseed.

**The Wilson gap at beat 3, stated exactly:** point accuracy 91.7% against a
Wilson lower bound of 81.9% — **9.8 percentage points of statistical caution
baked into the number the ladder actually reads**, on 60 acted decisions.

**Before and after limits at beat 9:** ₹5,000 (rung 3) before the clawback;
**₹2,500 (rung 2)** after — one rung, exactly as `ladder.py`'s
`max(current_rung - 1, 0)` guarantees, with no `POST
/recommendations/{id}/approve` call anywhere in the sequence.

---

## ARCHITECTURE AND TECH

### Every technology used

| Technology | Role | Licence (as declared in the project's own stack page, `interactivehtml/index.html`) |
|---|---|---|
| Python 3.11 | Trust engine, backend, governance, simulator, assistant | PSF |
| FastAPI | API surface, auto-generated OpenAPI schema | MIT |
| PostgreSQL | Append-only decision, policy, and audit tables | PostgreSQL licence |
| SQLAlchemy + Alembic | ORM and versioned schema migrations | MIT |
| LangGraph | Governance coordinator, four agent nodes | MIT |
| Google Gemini | Agent narratives, assistant answers, retrieval embeddings; cached mode is the demo default | Free tier |
| Azure OpenAI (`gpt-4.1-mini`) | Optional fourth chat provider for the assistant, not embeddings — **on a finished, unmerged branch, not yet on `main`** (§ below) | Paid, opt-in only, never required |
| Pydantic | Structured LLM output validation, API schemas | MIT |
| Next.js + TypeScript | Administrator dashboard | MIT |
| Tailwind + Recharts | Styling, confidence-band charts | MIT |
| Typer + httpx | Simulator CLI and its HTTP client | MIT / BSD |
| pytest + Hypothesis | 1,004 tests including property-based statistics and policy tests | MIT |
| Docker Compose | Reproducible local environment | Apache 2.0 |
| GitHub Actions | CI: lint, tests, schema and index freshness checks | Free tier |
| JWT + RBAC | Admin, reviewer, auditor roles | MIT |

### What was deliberately excluded, and the ADR that records why

| Excluded | ADR | Why |
|---|---|---|
| Four deployed microservices | ADR-0008 | A monorepo with in-process calls and import-rule/CI-enforced boundaries is stronger than a network hop for a four-person, fixed-deadline capstone — extracting a real service later is a deployment change, not a rewrite |
| A vector database (Chroma/pgvector/Pinecone/etc.) for the assistant's retrieval index | ADR-0015 (Proposed) | 135 chunks is 135 dot products; a vector DB would reverse ADR-0008's own reasoning without the circumstances having changed |
| Redis, Celery | `docker-compose.yml`'s own comment; ADR-0008's scope | Cut from scope for the capstone timeline; would need its own ADR to add back |
| Real bank/ERP/payment integration | `docs/CONTEXT.md`'s Explicit non-goals | Everything runs against the simulator's synthetic invoices |
| Production-grade auth beyond a JWT/RBAC scaffold | `docs/CONTEXT.md`'s Explicit non-goals | Capstone prototype, not a hardened multi-tenant system |
| Multi-tenant support, HA/scale target | `docs/CONTEXT.md`'s Explicit non-goals | Single agent, single demo environment |

### Boundary rules and how each is enforced in code

| Boundary | Rule | Enforcing test file(s) |
|---|---|---|
| `trust/` | No FastAPI, SQLAlchemy/psycopg, Redis, Celery, network calls, wall-clock reads, or global mutable state | The strongest form of enforcement in the codebase, if the least automated: `trust/pyproject.toml` declares **zero runtime dependencies** (`dependencies = []`) — a forbidden import couldn't be added without first editing a one-line, highly visible file, which is itself a review trigger. No dedicated AST test file exists for this lane beyond that |
| `governance/` | No SQLAlchemy, psycopg, FastAPI, or `backend.*` imports | Same — manually audited, no dedicated AST test file found |
| `backend/app/policy/` | No ORM, database, network, or LLM import | `backend/tests/test_policy_import_boundary.py` |
| `assistant/` | No database, no `backend`/`app` import, no second LLM SDK, no vector database, no heavyweight numeric stack | **`assistant/tests/test_import_boundary.py`** — a real AST-based test (`ast.parse`, walks every import in every non-test `.py` file, asserts against a `FORBIDDEN_TOP_LEVEL_MODULES` frozenset), wired into CI |
| `simulator/` | No backend import, no direct database access | Manually audited, no dedicated AST test file found |

**Say on stage:** "The newest lane, `assistant/`, is the one with the boundary
rule actually written as code — an AST walk over every import, not a person
remembering to grep before merging."

### The three governance modes

From `governance/governance/modes.py`:

| Mode | What it does | When |
|---|---|---|
| `stub` | No LLM call, canned data, fully deterministic | **Default** — an unset environment must never reach for a fixture directory that may not exist or be one typo from a live call |
| `cached` | Replays a recorded response from an on-disk store | **The demo default** — "a recorded response cannot rate-limit, time out, or fail in front of a panel" (the module's own docstring) |
| `live` | A real provider API call, with a timeout and fallback to the matching recording on failure | Opt-in, for a rehearsed live segment |

### Provider independence

Four `GOVERNANCE_PROVIDER` values exist in the codebase, behind one
`LLMClient` protocol (`governance/governance/llm/base.py`): **Gemini**
(`gemini.py`, raw HTTP, the default, free tier), **Claude** (`claude.py`, via
the `anthropic` SDK, optional), **OpenAI** (`openai_client.py`, via the
`openai` SDK, optional), and **Azure OpenAI** (`azure_openai.py`, raw
`httpx`, chat-only — **on the finished-but-unmerged branch behind PR #51**,
not yet on `main`). Selection is per-agent
(`GOVERNANCE_PROVIDER_<AGENT>` overrides the default), and the recording
cache key includes the model (`agent.promptversion.model.evidence`) so a
mixed-provider panel can never silently replay one provider's recording for
another's request.

**Honest caveat, worth stating precisely rather than glossing over:** the
default, shipped configuration runs **all four governance agents on the same
provider (Gemini)** — the per-agent override exists in code and is real, but
is not the default. ADR-0012 (still `Status: Proposed`) names this directly:
*"They are four prompts against one base model, so they inherit that
model's biases and their errors correlate."*

---

## WHY THIS IS DIFFERENT

From `interactivehtml/index.html`'s own landscape-research section, quoted
precisely, not paraphrased:

> "The closest software prior art overlaps us on pieces of the shape — a
> governance layer, human-in-the-loop approval, risk-graded actions — but
> none of it raises or lowers an authority limit on the basis of measured
> accuracy. That gap is the project."

| Closest prior art | Overlaps on | Repriced by measured accuracy? |
|---|---|---|
| Unit21 ("progressive autonomy trust ladder", L0–L3) | The rung design itself | Not established by this review — named as the closest structural match, not confirmed to fail this test |
| Monte Carlo Data (autonomy as a "trust score") | Framing autonomy as a score | Not established by this review |
| `evidence-gate/agentgov` | Governance layer, human-in-the-loop approval, risk-graded action classification, approval-queue dashboard | **No** — rule-based; "each rule, no LLM-based guardrails" by its own docs |
| VERITAS OS | Decision control, policy enforcement, audit trails, replayable evidence | **No** — runtime enforcement only, no earned-autonomy mechanism |
| HumanLayer | Approval gates and escalation paths around tool calls | **No** — human-in-the-loop plumbing only, no trust model |
| Microsoft Agent Governance Toolkit (MIT, Apr 2026) | Open-source runtime security for agents | **No** — security posture, not autonomy calibration |
| Anthropic's `claude-code` repo | An open feature request for a similar "ask before acting → act and report → full autonomy" ladder | Not a shipped system |
| **This project** | Same shape — governance layer, human-in-the-loop, risk-graded actions | **Yes** — a Wilson lower bound on measured accuracy gates the ladder |

The one academic overlap: *Governing What You Cannot Observe* (Marín &
Chaudhary, University of Turku, `arXiv:2604.24686`, April 2026 — "RiskGate"),
which shares this project's drift-detection and adaptive-threshold math, then
argues against putting an LLM anywhere in a governance loop: *"LLM-based
evaluators introduce latency, cost, and the recursive problem of governing
the governor."* This project's own answer, direct: that objection lands on
systems where the LLM **is** the governor; here it never is — statistics
compute the evidence, deterministic code enforces it, a human authorizes
every increase, and the LLM writes only the rationale a reviewer signs off
on. The same page notes RiskGate "runs with no human in its authorization
loop at all and no empirical evaluation of its own" — this project has both.

**The page's own honest limitation, quoted:** *"This review found no
duplicate of the specific construction — Wilson-bound gating of a ladder,
argued over by a non-authoritative multi-agent panel, with asymmetric
clawback — but the nearest neighbors are a research paper with no running
system and open-source tools that solve adjacent problems, not shipped
products at feature parity. This remains a prototype demonstrating a
mechanism in one decision category with a simulated decision stream."**

### What the original EOI proposed vs. what was built

**No EOI document exists anywhere in this repository** — this audit searched
for it and found nothing; if the mentors hold a copy, this section cannot be
checked against it directly. What follows is reconstructed from what the
repo's own docs say was narrowed, not from the EOI text itself:

- **Scope narrowed to one agent, one decision category (invoice
  approve/reject/escalate)**, stated explicitly as a non-goal:
  `docs/CONTEXT.md:259-260`, "No claim that this generalizes beyond invoice
  approval without further design work."
- **`shared/`'s v1.1 contracts were frozen over an independently-designed
  alternative** built in parallel on `origin/ad/simulator-frontend` (a
  3-tier × category-limit table, `AgentDecisionRecord`, 13 lowercase reason
  codes) — `docs/adr/0010-main-shared-contracts-canonical.md` records the
  decision to treat `main`'s 5-rung, 18-code design as canonical and port
  the divergent branch rather than merge or discard it
  (`docs/audits/2026-08-23-port-feasibility.md` has the file-by-file plan).
- **Azure as the primary LLM provider was proposed and not adopted as the
  default** — Gemini remains default throughout; an Azure OpenAI provider
  exists, finished, chat-only, opt-in, on an unmerged branch (§ above), not
  the "Azure primary" pivot earlier audits in this series found undocumented
  and unimplemented for weeks.

---

## ENGINEERING RIGOUR

**Wilson cross-validated against statsmodels as an independent oracle.**
`trust/tests/test_wilson.py::test_matches_statsmodels_reference_implementation`
— `pytest.importorskip("statsmodels.stats.proportion")`, so the test skips
cleanly in an environment without the package rather than failing, but runs
and passes when it's installed.

**Property-based tests via Hypothesis.** Two real property suites, not
example-based tests dressed up:
- `trust/tests/test_wilson_properties.py` — 8 properties, including "the
  interval is always a valid probability range," "the observed rate always
  falls inside the interval," "one more correct decision never lowers the
  bound," "the bound is never optimistic," and "impossible inputs are
  rejected loudly."
- `backend/tests/test_policy_properties.py` — 5 properties on the Policy
  Engine, including "never allows an amount above the limit," "clamp never
  rises above the evidence-supported limit," and "clamp is deterministic."

**The two concurrency races found under real load, and the measured
failure rate before and after.** Two independent live measurements exist —
the original discovery (`docs/audits/2026-09-06-audit.md` §1a, a load test
across several concurrency levels) and the fix's own before/after
verification (`docs/DECISION_LOG.md`, PR #31 entry, 2026-09-07) — both real,
from two separate live-Postgres test runs, not a single number restated
twice:
- **Race 1** (`decisions.py`): an unlocked `SELECT max(sequence)`
  read-then-insert raced under concurrency, colliding on
  `uq_decisions_agent_sequence`, surfacing as an unhandled 500. **The fix's
  own before/after verification: 78.4% of calls failing at 40-way
  concurrency before the fix, 0% after** (`docs/DECISION_LOG.md`, PR #31).
  The original discovery audit measured a range across concurrency levels on
  a separate run: 49.7% failing at 40 concurrent (746/1500), still 7.7%
  failing at just 2 concurrent (46/600) — "the default outcome of any two
  decisions for the same agent landing close together in time," not a rare
  edge case. Fixed with `SELECT ... FOR UPDATE`, serializing per agent.
- **Race 2** (`audit_log.py`): an unlocked read-then-append let two
  concurrent appends chain off the same predecessor — no exception, a
  **silently forked hash chain**. Measured live: **59 forked `prev_hash`
  groups out of 113 rows** before the fix (`docs/DECISION_LOG.md`, PR #31).
  Fixed with a transaction-scoped Postgres advisory lock **plus** a new
  `log_seq` column (migration `0003`) — the advisory lock alone was
  confirmed insufficient without it (the fix's own test still failed with
  only the lock, before `log_seq` was added), since `ts` is caller-supplied
  wall-clock time with no guaranteed relationship to true insertion order.

**A bug invisible on SQLite, found only on Postgres.** The exact bug the
task description points at ("commit-visibility lag") is documented in PR
#48's own body: `POST /decisions` committed in dependency teardown, after
the response was already sent — measured live, **18 of 40 rows visible
immediately, 22 of 40 at 28–97ms later; 96 of 200 read-back calls 404'd**
before the fix (mutating routes now commit before building the response). A
second, related ordering bug surfaced later, also Postgres-only in practice:
`GET /audit-log`'s chain verifier read hash-chain order by caller-supplied
`ts` rather than the monotonic `log_seq` column — invisible until the
escalation-ruling change roughly doubled writes per run and many landed
within the same wall-clock second, where `ts` ordering is undefined.
Measured on the live database: **2,912 entries, 0 broken hashes, 0 real
gaps — 11 false-positive "tampering" alarms** from `ts` ties, now fixed to
read `log_seq`.

**Deterministic simulation, byte-identical across runs and
`PYTHONHASHSEED`.** `.github/workflows/ci.yml` runs the simulator CLI twice
per phase with two different `PYTHONHASHSEED` values and `diff`s the
fixture output, plus a separate step that runs the demo arc twice and diffs
stdout — both are real CI gates, not a manual claim.

**Import-boundary tests enforcing architecture in CI.**
`backend/tests/test_policy_import_boundary.py` (the Policy Engine) and
`assistant/tests/test_import_boundary.py` (the newest lane, and the more
thorough of the two — a real AST walk, not a grep) are both wired into CI.
`trust/`, `governance/`, and `simulator/`'s own boundary rules are enforced
by manual audit each pass, not by an equivalent automated test — worth
naming honestly rather than claiming five-for-five.

**The hash chain: live verification and a tamper test.** `GET /audit-log`
recomputes and verifies the full chain on every call (not a cached verdict);
`backend/tests/test_models_audit_hash.py`, `test_models_guards.py`,
`test_audit.py`, and the newest `test_audit_chain_order.py` collectively
include a test that tampers with a stored payload directly, bypassing the
ORM guard, to confirm verification does not simply become permissive.

**One real asymmetry, worth stating rather than hiding:** `frontend/` has
**zero automated tests** — confirmed by direct search for `.test.` files
and a `tests/` directory (which exists but holds only a `.gitkeep`). Every
other lane carries substantial, independently-run test coverage (see Scale
and Effort above); the frontend's own correctness discipline is `npm run
typecheck` and `npm run build` passing clean, not a test suite. Say this
plainly if asked "what's your weakest-tested surface" — it has a clean,
one-word answer.

**Five point-in-time audits committed to `main`**, plus four more produced
as read-only working sessions in this same series (not committed, per the
convention every one of them states up front): `2026-08-21-pre-merge-audit.md`
is the one that documents the team's own coordination failure and its root
cause in detail — two branches (`uk/trust`, `uk/shared-trust-contracts`)
diverged independently from the same base commit because the lane briefs
and deadline sheet were never committed to git (`docs/RISKS.md` R11: "the
direct root cause of R9," a ~35,600-line independent redesign of the frozen
contracts that had to be ported rather than merged).

---

## HONEST LIMITATIONS

State these plainly — every one is better said by us than found by them.

**One agent, one decision category.** `docs/CONTEXT.md:259-260`: "No claim
that this generalizes beyond invoice approval without further design work."
Scoped this way because a five-week, four-person capstone cannot build and
prove a general mechanism and a specific one in the same timeline; the
5-rung ladder and Wilson-gated trust score are the reusable core, and
extending to a second decision category is a real, scoped, not-yet-started
piece of future work (see below). Closing it needs: a second `AgentContext`
shape (or a category dimension on the existing one), and a decision on
whether trust is per-agent or per-agent-per-category — not decided anywhere
in the current docs.

**The demo runs on recorded LLM responses, not live calls, by default.**
`governance/governance/modes.py`: `cached` is the demo default, explicitly
because "a recorded response cannot rate-limit, time out, or fail in front
of a panel." `live` mode exists, is implemented with a timeout and fallback,
and can be demonstrated deliberately. Scoped this way because a free-tier
API key (20 requests/day on Gemini's free tier, per earlier audits in this
series) makes a from-scratch bad idea to depend on live-mode for a scored
defense.

**Clawback evaluates at run boundaries, not continuously.**
`backend/app/services/simulation.py`'s own inline comment and
`docs/adr/0004-...md`'s dated addendum both say this explicitly: the trigger
is "at the end of a simulation run," deliberately not on every decision
ingest, because a full trust evaluation (`load_decision_records` plus
`trust_engine.evaluate` over an agent's entire history) on every single
write is both slow and wasteful. Stated as a scoped prototype limitation, not
discovered — a real deployment would evaluate on a schedule or from the
ingest path with its own rate limiting.

**Audit sampling: the selection and queue are real; the evidence feedback
loop is not closed — verified precisely, not assumed.** Selection at
ingest (`sampling_rate_of(agent.current_rung)`), a real review queue, and a
persisting review endpoint (`POST /audit-samples/{id}/review`) all exist and
work — confirmed by reading `backend/app/api/v1/audit.py:90-169` directly.
A `DISAGREED` verdict correctly emits `SAMPLE_REVIEW_DISAGREEMENT` onto a
hash-chained audit-log entry. **But the review deliberately never overwrites
the decision's recorded ground truth, and nothing feeds a review's verdict
back into the trust evaluation's evidence** — the code's own docstring
states why: `TrustEvaluation` has no field distinguishing an accuracy
estimate built from full ground truth (the simulator) from one built from a
5%-reviewed sample (production), and adding one is "a proposed-but-deferred
contract change" (ADR-0009's own Consequences) that touches a frozen
`shared/` type requiring all four reviewers — "not being made unilaterally
two days before the defence" (`docs/DECISION_LOG.md`, 2026-09-13 entry, in
those words). This is also why `SAMPLE_EVIDENCE_INSUFFICIENT` remains the
one unreachable reason code of 18.

**Assistant scoping is context isolation, not access control.**
`backend/app/api/v1/assistant.py`'s own module docstring, quoted exactly:
*"Nothing here checks whether the caller is allowed to see that agent —
any authenticated user who can open agent X's detail page gets agent X's
assistant... Do not describe this as a permission boundary; it is not
one."* Verified live (2026-09-12 audit): asking about agent-03 by name
inside an agent-01-scoped conversation produces zero agent-03 data in the
assembled context — genuine data isolation — but no per-agent RBAC exists
in this system at all (`app/deps.py` has three roles, none agent-scoped), so
this is the same exposure every other agent-detail route already carries,
not a weaker one specific to the assistant.

**The four-agent governance panel is not yet running on independent
models.** Covered above under Provider Independence — real per-agent
provider selection exists in code, but the shipped default runs all four
agents on Gemini, so the "four independent judges" framing is a design
target with the seam already built, not yet a fact about the demo
configuration.

**A newly-found gap this audit surfaced: the assistant's own retrieval
index is currently stale relative to a fact the rest of the system already
corrected.** Full detail in `docs/audits/2026-09-14-final-audit.md` §2 and
§5. `assistant/index.json` still quotes the disproven "reset to the floor"
description of `CLAWBACK_CRITICAL_ERROR`; `shared/reason_codes.py` has
already been corrected to "reduced one rung." The CI check that would catch
this (`python -m assistant check`) is currently soft-disabled
(`continue-on-error: true`) rather than fixed. Closing it needs a live
`GEMINI_API_KEY` and `python -m assistant build` — roughly 1-2 hours, not a
design question.

---

## FUTURE SCOPE

Only what's actually recorded, cited to its source:

| Item | Recorded where | What closing it would take |
|---|---|---|
| A `TrustEvaluation` field distinguishing full-ground-truth accuracy from sample-based accuracy | ADR-0009 Consequences, "proposed-but-deferred... not made here since it would alter an existing type" | A `shared/` contract change, needing all four lane owners' sign-off (ADR-0005) |
| Whether an already-promoted agent's prior samples get re-weighted at the new rung's rate, or only future ones do | ADR-0009 Consequences, "an open implementation question this ADR does not resolve" | A team decision, then an implementation in `backend/app/services/audit_sampling.py` |
| Downstream signals (payment reversal, vendor dispute, reconciliation mismatch) as a supplementary ground-truth input | ADR-0009 Alternatives considered — rejected as a *sole* mechanism, left open as a *supplementary* one | A new ingestion path plus a decision on how it composes with sampled review evidence |
| A second decision category, or a per-category dimension on trust | Not named directly by any ADR; the underlying gap is `docs/CONTEXT.md`'s non-goals ("no claim this generalizes beyond invoice approval") and the open `ground_truth` question (`docs/CONTEXT.md:157-161`) | A category dimension on `AgentContext`/`DecisionRecord`, and a decision on per-agent vs. per-agent-per-category trust — neither designed yet |
| Real agent credentials rather than an `X-User-Role` header | Not found recorded in any ADR or audit as a named future item — `app/deps.py`'s current RBAC is explicitly a "scaffold" per `docs/CONTEXT.md`'s non-goals, but no document proposes a specific replacement mechanism; stating this gap rather than inventing a plan for it | Unscoped — would need its own ADR |
| Continuous (not batch-boundary) clawback evaluation | ADR-0004's 2026-09-13 addendum, explicit: "A real deployment would evaluate on a schedule, or from the ingest path itself with its own rate limiting — either is a reasonable choice this prototype simply hasn't had to make" | A scheduler or ingest-path hook, plus rate limiting design |
| Integration adapters for an existing agent system | Not found recorded anywhere in the ADRs, audits, or CONTEXT.md — there is no adapter layer, real or planned, named in the repository | Unscoped — this is a genuine gap in the documented plan, not a deferred-but-designed item, and should be named as such rather than implied to exist |
| A model-provenance field on `AgentOpinion` (which model argued which opinion) | ADR-0012 Alternatives considered — "the right long-term shape... lost for now because `shared/` is frozen... worth revisiting after the freeze" | A `shared/` contract change, four-reviewer sign-off |
| Multi-provider governance actually enabled by default (not just possible) | ADR-0012, still `Status: Proposed`, needs "a decision from the team" per its own header | A team ruling on the paid-API lane-brief constraint, then flipping the default env config |

---

## QUESTIONS AND ANSWERS

Each grounded in a specific file, ADR, or measured number — several are the
project's own pre-written "defend it" lines (`docs/SYSTEM-EXPLAINED.md` §6),
quoted because they're already precise, not because they're ours to
improve on.

**"Isn't this an LLM deciding whether to trust another LLM?"**
No — the decision rests on a computable number with a documented formula;
run it twice, get the same answer. The LLM contributes an explanation a
human can read, not the verdict (ADR-0001; `docs/SYSTEM-EXPLAINED.md` §6).
Concretely: `trust_score` is pure arithmetic in `trust/` — zero LLM calls,
zero network — and even the *direction* (INCREASE/HOLD/CLAWBACK) is computed
by `trust_engine.ladder.evaluate_ladder()` before governance's four agents
ever see the evaluation. Governance can only argue about an already-computed
number; it cannot originate one.

**"What if the LLM hallucinates a recommendation?"**
Three independent backstops, all in code, none of them another LLM call:
(1) structured-output validation raises `OpinionParseError` rather than
accepting malformed JSON; (2) `clamp_recommendation`
(`backend/app/services/governance.py`) enforces the trust engine's own
evidence-supported limit regardless of what governance's panel asks for —
`RECOMMENDATION_CLAMPED` is a real, reachable reason code, not a theoretical
one (confirmed live in this session's own demo run, beat 4's clamp example
in the seed data: proposed rung 4, clamped to rung 3); (3) a human must
approve any INCREASE regardless — a hallucinated proposal can be declined,
never self-executes.

**"In production you don't know ground truth, so what are you measuring?"**
"The strongest attack on the whole premise... have this ready — and it
doubles as the ROI story, since the review burden falls exactly as trust
rises" (ADR-0009's own defend-it line). The honest follow-up, stated
precisely rather than glossed: audit sampling's selection and review queue
are real and working today; the loop back into the trust score's own
evidence is not yet closed, deliberately, pending a `shared/` contract
change that needs all four reviewers (see Honest Limitations above). Say
this second part before a panel finds it themselves.

**"Why do clawbacks not need human approval?"**
"The risk profile is asymmetric, so the controls are asymmetric: removing
authority is always safe, granting it is not. Same logic as revoking access
immediately but restoring it through a process" (ADR-0004's defend-it line).
Measured, not asserted: this session's own demo run showed a clawback drop
₹5,000→₹2,500 with zero calls to `/approve` anywhere in the sequence (beat 9).

**"Why only one decision category?"**
Scope, stated as a non-goal rather than discovered as a limitation:
`docs/CONTEXT.md`'s Explicit non-goals, "No claim that this generalizes
beyond invoice approval without further design work." A five-week,
four-person build proving one mechanism rigorously was judged better than
proving a generalized one shallowly — see Future Scope above for exactly
what extending it would need.

**"Why four agents rather than one prompt?"**
`Recommendation.has_dissent` exists because a split panel is the most
useful thing on a reviewer's screen — preserving disagreement rather than
blending it into one output (ADR-0012's Context). The honest second half,
stated in the same ADR rather than hidden: "they are four prompts against
one base model, so they inherit that model's biases and their errors
correlate" — the swappable-provider mechanism exists specifically to answer
this, but is not the shipped default (see Honest Limitations above). "Even
four agents wrong in the same direction cannot move an autonomy limit" —
the structural answer ADR-0012 gives first, correct but "not sufficient" by
its own admission, which is why the provider work exists at all.

**"How does this integrate with an existing agent?"**
Honestly: it doesn't yet, and no document in this repository proposes a
specific adapter (Future Scope above). What exists is a real HTTP contract
(`POST /decisions`) any decision-making system could call — the simulator is
one such caller, proving the seam works, not the only one it could support.

**"What happens if the governance layer is unavailable?"**
"The system stays safe — the enforcement path contains no LLM and no
network call. Worst case, no recommendations get generated and autonomy
simply stops changing" (ADR-0003's defend-it line). Concretely, verified in
code: `generate_recommendation` and the assistant's own `generate_reply`
both raise a `503 service_unavailable` rather than guessing — "a 503 says
'governance is unavailable right now,' which is the truth, rather than
guessing at an answer with nothing behind it"
(`backend/app/services/governance.py`'s own comment, and
`app/api/v1/assistant.py`'s mirrored handling of the same failure mode).
