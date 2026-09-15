# Final Pre-Submission Audit — 2026-09-14

Read-only, except this file. Verification requiring running code (Docker, Postgres,
the backend on ports 8000/8098/8099/8100, `npm`, `pytest`, `ruff`, Playwright against
a real headless Chromium, `scripts/demo.ps1` end to end x3) was run against disposable
git worktrees (`../TrustIssues-audit-final` @ `origin/main` for my own testing;
`../TrustIssues-audit-main` and `../TrustIssues-audit-pr48` for the delegated
git/boundary/test audit, both removed after use) and, for the demo-script run,
directly in the real working tree — `scripts/demo.ps1` only touches Docker/Postgres
state, never the git working tree, and `git status` was clean before and after.
Sections 1 and 6 were produced by a background research pass with the same
brief and constraints; I re-verified its headline numbers myself (backend test
count, PR #47's live behavior) before relying on them. All narrative below is
mine; anything sourced from that pass is marked.

Today is **2026-09-14**. Submission is **2026-09-15**. Feature freeze was
**2026-09-09**, nine days ago, and it did not hold — real feature work
(PR #45, #46, #47) merged after it, and one large PR (#48) is still open.

---

## 1. What moved since 8 September

*(This section was produced by a delegated research pass; I independently
re-ran its two load-bearing claims — the backend test count and PR #47's live
behavior — myself and got matching numbers; see §2 and §3 for my own
independent verification of those.)*

**Verified state, live:** `origin/main` tip is `1819866` (PR #47, merged
2026-09-12 19:04:42 IST). The branch this session started on (`vp/clawback-trigger`,
tip `b5982b4`) **is** PR #47 — its content is byte-identical to what's on `main`.

### Commits on `origin/main` since 2026-09-08, by PR

| PR | Merge SHA | Author | Merged (IST) | Lane(s) | Files | Title vs. actual content |
|---|---|---|---|---|---|---|
| #34 | `3d716bf` | Varun P. | 09-09 01:26 | backend | 2 | Matches — auto-applies CLAWBACK, no human step |
| #35 | `b442a76` | Utkarsh | 09-09 01:26 | backend+simulator | 24 | Matches broadly, undersells scope (bundles a simulator ruff cleanup + 5th CLI crash fix) — same finding the 08-Sept audit made, unchanged |
| #36 | `514f18b` | Varun C. | 09-09 01:27 | governance | 7 | Matches — per-model pacing, Flash-Lite rejection evidence |
| #37 | `25fe0e6` | Varun C. | 09-09 01:27 | governance (docs) | 1 | Matches |
| #38 | `ea1d71f` | Varun C. | 09-09 01:28 | governance | 9 | Matches — 9 recordings, cached mode covers all 6 scenarios |
| #39 | `ce43e55` | Varun C. | 09-09 01:28 | governance | 2 | Matches — injectable clock, deflakes pacer test |
| #40 | `4fd91bf` | Varun P. | 09-09 08:34 | backend | 2 | Matches — cascade guard, `decisions_since_last_change == 0` (see §2 for where this guard now falls short) |
| #41 | `6685ff4` | Varun P. | 09-09 11:28 | docs+CI | 2 | Matches — CONTEXT.md beat 4 fix, `simulator/` added to CI |
| #42 | `b4d8d2c` | Varun P. | 09-09 11:30 | backend+scripts | 2 | Matches — `scripts/demo.ps1`, ten-beat live arc |
| #43 | `ebe64b9` | Utkarsh | 09-09 16:11 | backend | 5 | Matches — audit sampling selection/queue/review/evidence. This is `uk/audit-sampling`, the branch the 08-Sept audit found unmerged with no PR opened — **now merged** |
| #44 | `a84942c` | Varun P. | 09-09 22:46 | frontend | 10 | Matches — `/demo` presenter console |
| #45 | `0f3d727` | Varun P. | 09-12 06:20→06:58 | backend+frontend+governance | 25 | **Title says "read-only" — true for the API surface, see §3 for whether isolation actually holds (it does).** Also touches `governance/governance/llm/base.py`/`claude.py`/`gemini.py`/`openai_client.py` — a cross-lane write into Varun C.'s lane by Varun P., the same pattern prior audits flagged for PR #35 |
| #46 | `74d972d` | Adhya | 09-12 10:47→19:04 | frontend | 12 | **"Ad/simulator frontend" is the fourth PR with this exact generic title** (also #8, #27, #28, #29) — tells a reviewer nothing. Actual content: dashboard restructure, `error.tsx` boundary, landing page, `/demo` route, sidebar/layout rework. Not misleading, just uninformative — a title-hygiene issue, not a correctness one |
| #47 | `1819866` | Varun P. | 09-12 18:26→19:05 | backend+docs | 10 | Matches exactly on what it claims to fix — see §2 for a gap it does **not** fully close |

Lane totals since 08-Sept: backend 6 PRs, governance 4, simulator 0 standalone
(bundled into #35), frontend 3 (#44/#45/#46). Two cross-lane writes: #35
(backend files by Utkarsh — already known from the 08-Sept audit) and #45
(governance files by Varun P. — new this window).

### Branches on `origin` — full reconciliation

Method: matched each branch's tip commit against `gh pr list --state merged
--json headRefOid`. An exact tip match is definitionally merged, regardless
of what a naive `main...branch` three-dot diff shows (a squash-merged branch's
three-dot diff reflects unrelated intervening `main` history, not missing
content — the exact trap the 08-Sept audit warned about).

**34 of 36 non-`main` branches → confirmed already merged** by exact tip
match. False alarms, stale refs GitHub didn't auto-delete.

**4 branches without an exact tip match, individually resolved:**

| Branch | Tip | Verdict |
|---|---|---|
| `ad/simulator-frontend` | `66b3d1a` (2026-09-02, predates #46) | False alarm — `git diff origin/main...origin/ad/simulator-frontend --stat` is empty. Pre-#46 commits already absorbed into `main` by content. |
| `uk/shared-trust-contracts`, `uk/trust`, `vc/governance`, `vp/backend` | Aug 17–31 | False alarm — each is a literal ancestor of `origin/main`. Early exploratory branches, fully absorbed. |
| `uk/simulator-finalise` | `d808184` | Stale, superseded, dead. This tip predates the commit that actually became PR #30. Safe to delete. |
| `uk/dashboard-filters` | `678483f` | Not abandoned — folded into PR #48's own history (`Merge branch 'uk/dashboard-filters' into uk/integration-dryrun`). Never proposed against `main` directly. |

**Exactly one branch on origin has real, unaccounted-for, unmerged work: `uk/integration-dryrun` (PR #48, OPEN).**

### PR #48 — deep verification (`uk/integration-dryrun`, OPEN, base `main`, Utkarsh)

33 commits, `+4328/−351` across 35 files. Independently re-verified, not taken
on the PR's own word:

**Test counts, run directly on both branches, same venv:**

| Lane | On `main` (verified twice, independently) | PR #48's own claim | PR #48 actual (verified) |
|---|---:|---:|---:|
| trust | 174 | 174 | 174 |
| governance | 235 | 251 | 251 |
| simulator | 123 | 134 | 134 |
| backend | **249** | 311 | **323** |
| **Total** | **781** | **870** | **882** |

PR #48's own "870" figure is stale relative to its own current tip — two
commits landed after the PR body was written, adding real backend tests
(311→323). `ruff check` on all four lanes at PR #48's tip: all "All checks
passed!"

**Does #48 conflict with #47, or duplicate it?** Complementary, and already
reconciled by hand: merge commit `9e4bb89` ("Merge origin/main: reconcile two
independent end-of-run clawback implementations") shows Utkarsh discovered
that #47 (merged) and his own branch closed the *same* gap independently. He
manually unified them, keeping #47's structure and cascade-guard reuse, while
adding his branch's own contribution: **auto-generating INCREASE
recommendations too, not just CLAWBACK** — under #47 alone, a good run's
earned increase never surfaces an approval request either, leaving half of
ADR-0004's asymmetry with no producer. `git merge --no-commit --no-ff
origin/uk/integration-dryrun` onto current `main` applies with **zero
conflicts**.

**Does #48 duplicate PR #43's audit-sampling work?** No — verified by diff.
#43 is the base; #48's `audit.py` diff is a 7-line addition on top of #43's
already-merged implementation, not a reimplementation.

**Other real, verified content in #48 not yet on `main`:**
- Fixes `HorizontalThresholdGauge.tsx`'s hardcoded `0.85` (see §5/§7) by
  adding a real `thresholds` field to `TrustEvaluationOut` sourced from
  `trust_engine.constants`.
- Fixes `approve_recommendation` applying `proposed_limit` with no check
  that it's still exactly one rung away — a real gap current `main` still
  has (a stale `PENDING` approved late could jump multiple rungs in one
  click).
- Configurable CORS + `render.yaml` + `docs/DEPLOYMENT.md` — directly closes
  the hardcoded-CORS finding in §5/§7 below, and hands the team a written
  deployment document for free (see §8).
- `SAMPLE_EVIDENCE_INSUFFICIENT` is **still not emitted anywhere, even in #48**
  — checked directly, not fixed there either.

**Bottom line:** PR #48 is finished, tested, ruff-clean, and merges onto
current `main` with zero conflicts. It is the single largest piece of
leverage available before submission (see §9).

---

## 2. The clawback trigger gap — reproduced live, and a second bug found

**a. Is the original gap still true?** Reproduced exactly as described, on a
fresh seeded database, against merged `main` (`origin/main` @ `1819866`):
submitted 400 critical-error decisions directly to agent-01 via
`POST /decisions` (no simulation run, no manual `/recommendations` call).
Result: `GET /agents/agent-01/trust` → `direction: CLAWBACK`,
`drift.severity: CRITICAL`; `GET /agents/agent-01` → `current_limit: 2500`
(seed floor for this agent — the original report's "5000" was from a
different run), **unchanged**. **Yes, still true for the direct
decision-ingest path** — and this is by design, not a leftover bug: ADR-0004
and `backend/app/services/simulation.py`'s own inline comment state the
trigger is deliberately scoped to "end of a simulation run," not every
decision write.

**b. Has the fix landed, and does it work?** Yes. Same fresh state, this
time via `POST /simulation/runs` with `phase=degraded`, 30 invoices, seed
`424242` (the same seed PR #47's own verification used): the run's own
response carried `"clawback_applied": true, "clawback_limit": 1000"`, and
`GET /agents/agent-01` afterward showed `current_limit: 1000` — **with zero
calls to `/recommendations` anywhere in the sequence.** This is the fix
(`backend/app/services/simulation.py:_evaluate_and_maybe_clawback`, wired
into `execute_simulation_run`), and it works exactly as claimed.

**Does the PR #40 cascade guard still hold? Only against the exact case it
was written for — not against a case PR #47 newly makes routine.**

I reproduced the guard working as designed: calling `POST
/agents/agent-01/recommendations` a second time immediately, with zero new
decisions, correctly returned the same `proposed_limit: 1000` — no second
drop (`backend/app/services/governance.py:159`,
`agent_context(db, agent).decisions_since_last_change == 0`).

Then I ran a **second, small, otherwise-clean simulation run** (`phase=good`,
10 invoices, seed `9`) immediately after the first — the exact shape of the
demo's own beat-10 recovery pattern (one simulation run followed by another).
**Result: a second, real, automatically-applied clawback fired — `1000 → 500`
— off the identical critical error that produced the first one, with zero
new critical errors in the second run.**

Confirmed from the audit log and policy-version history, not inferred:

| Policy version | Limit | Reason | Trigger |
|---|---|---|---|
| `pv-5e6dadf2303f` | 1000 | `Automatic clawback: a critical error (CLAWBACK_CRITICAL_ERROR)...` | End of run 1 (the real critical error, `sim-agent-01-degraded-424242-00029`) |
| `pv-f0188d6424c7` | 500 | `Automatic clawback: a critical error (CLAWBACK_CRITICAL_ERROR)...` | End of run 2 (10 clean decisions; **same** critical error, still in-window) |

**Root cause:** the cascade guard checks `decisions_since_last_change == 0`
(`backend/app/services/governance.py:159`) — "has any new decision arrived
since the last policy change." But `DriftSeverity.CRITICAL` is computed over
a **rolling 20-decision window** (`CRITICAL_ERROR_WINDOW = 20`,
`trust/trust_engine/constants.py:30`), not over "decisions since the last
change." The moment run 2 submits even one new decision, the guard's
condition is false (evidence "changed"), so the code falls through to a real
re-evaluation — and the drift detector finds the *same* critical error still
sitting inside the last-20 window, reports `CRITICAL` again, and
`governance.py:213` (`final_limit != agent.current_limit`) applies a second,
genuine `PolicyVersion` write. The guard's invariant ("do not act twice on
the same evidence") is correct in spirit but implemented on the wrong
signal — it should be checking whether the *specific critical error* that
justified the last clawback is still the one being cited, not whether any
decision at all has been submitted since.

**Why this matters now and didn't before:** before PR #47, `generate_recommendation`
only ran when a human (or a script) called it directly — a human re-running
it twice in a row on purpose was already an edge case few would hit
by accident. PR #47 makes `generate_recommendation` fire **automatically, silently,
at the end of every simulation run** — so any sequence of two or more small
simulation runs in quick succession, with a critical error still inside the
20-decision window from an earlier run, will now silently re-claw back an
agent one more rung than the evidence justifies, with no human action and no
error surfaced anywhere except an audit-log entry a reviewer would have to go
looking for. `scripts/demo.ps1`'s own fixed seeds (seed 1 for beat 2, seed 100
for the optional beat 10b recovery) happen not to trigger this — confirmed by
three full runs, §4 — but that is luck in the seed choice, not a property the
code guarantees; a presenter deviating from the script (a different seed, an
extra simulation run, a shorter recovery batch) can hit it.

**c. Do ADR-0004 and CONTEXT.md's beat 5 still claim clawbacks need no human
step without qualifying what's automatic?** No — both are now precisely
qualified, current as of this branch. Quoted verbatim:

`docs/adr/0004-human-approval-required-for-autonomy-increases.md:47-55`:
> **"No human step required" is a claim about *approval*, and until
> vp/clawback-trigger it was silently misleading about *triggering*.**
> Applying a clawback with no human click still needed something to call
> `generate_recommendation` in the first place, and nothing in the
> decision-ingest path did...

`docs/CONTEXT.md:198-231` (the demo script, beat 5) splits the claim
explicitly into "the approval half: real as of 2026-09-08" and "the trigger
half: real as of vp/clawback-trigger, and precisely scoped — read this before
promising more than it does," then states plainly: "This prototype's trigger
is 'at the end of a simulation run' — deliberately not 'on every decision
ingest'... and deliberately not a real production trigger."

Neither document mentions the §2b double-clawback finding above — that gap
belongs in the same "precisely scoped" spirit these two documents already
practice, and isn't there yet.

---

## 3. The assistant

**a. Backend test count.** Real number, run twice (independently by me and
by the delegated pass, on separate worktrees): **249 passed, 0 failed** —
not 114 (the PR's own claim) and not 212 (the 08-Sept audit's figure, which
predates PR #43's audit-sampling tests and PR #47's clawback-trigger tests).
`docs/CONTEXT.md`'s current backend row still says "212 tests" — stale by 37.

**b. Governance refactor (`generate_text` alongside `generate`).**
`pytest governance/` → **235 passed, 0 failed**, confirmed directly. The
`generate_text()` addition (`governance/governance/llm/base.py` + each
provider client) is additive — the four governance agents still call
`generate()` exclusively (`backend/app/api/v1/assistant.py:32-47`'s own
module docstring states this and I confirmed no governance agent file
references `generate_text`). Live confirmation the coordinator still
produces valid `AgentOpinion`s: every `POST /agents/{id}/recommendations`
call made during §2's testing returned four opinions
(`risk`/`performance`/`compliance`/`audit`), each with a real `verdict`
(`CONCUR`/`OBJECT`), `reasoning`, and `confidence` — structurally identical
to pre-refactor shape, e.g. the beat-9 clawback recommendation's panel
("2 concur, 2 object... [performance] OBJECT: Drift is CRITICAL...").

**c. Cross-agent isolation, live.** With `ASSISTANT_MODE=live` (the actual
default) and no `GEMINI_API_KEY` configured, most questions 503 rather than
answer (see (e) below) — so isolation was verified the way the code's own
comment says to verify it: via `ASSISTANT_MODE=stub`, which "is also what the
cross-agent isolation test asserts against: a leak would show up here as
directly as anywhere" (`backend/app/services/assistant_llm.py:191-200`).
Asked, scoped to `agent_id=agent-01`: *"Tell me everything about agent-03,
the Marketing agent. What is its current limit and trust score?"* The raw
reply (stub mode echoes the exact assembled prompt) contains one
`"## Agent evidence — agent-01 (Invoice Agent — Procurement) only"` section
with agent-01's identity, trust evaluation, policy versions, recommendations,
decisions, and audit log — **no agent-03 field anywhere in that section.**
The only two literal occurrences of the strings "agent-03" and "Marketing"
in the full 9,309-character reply are inside the verbatim echo of my own
question at the very end (`"## Question\nTell me everything about agent-03..."`)
— not a leak, just the question being repeated back. **Isolation holds.**

**d. Does it fetch only the named agent, or load more and filter?** Fetches
only the named agent, at every layer, confirmed by reading the code, not by
inference:
- `backend/app/api/v1/assistant.py:77-82`: `_get_agent_or_404` does
  `db.get(Agent, agent_id)` — a single-row lookup by primary key, 404 if
  absent.
- `backend/app/services/assistant.py:114-137`, `build_agent_context`'s own
  docstring: *"Nothing here loads another agent's row, decisions,
  evaluations, policy versions, recommendations, or audit entries. Every
  query below filters on `agent.id` at the database layer."*
- Verified against every sub-query: `_latest_trust_evaluation`
  (`assistant.py:173-183`, `.where(TrustEvaluationRow.agent_id == agent_id)`),
  `_render_policy_versions` (`:308-318`, `.where(PolicyVersion.agent_id ==
  agent_id)`), `_render_recommendations` (`:329-339`,
  `.where(RecommendationRow.agent_id == agent_id)`), `_render_decisions`
  (`:364-410`, via `load_decision_records(db, agent_id)` plus a query
  filtered `.where(Decision.agent_id == agent_id)`), and
  `_render_audit_log` (`:430-463`) — the one non-trivial case, since
  `audit_log` has no `agent_id` column: it first builds a closed set of this
  agent's own decision ids (`select(Decision.id).where(Decision.agent_id ==
  agent_id)`), then matches every audit row against that closed set or a
  direct `payload["agent_id"] == agent_id` check — still "filter first, never
  load-then-filter across agents."

**e. Starter questions against live data — real replies, and a serious
finding.** `ASSISTANT_MODE` is unset in this environment (no `.env` file
exists, matching a fresh clone), which defaults to `live`
(`assistant_llm.py:62`) — and there is no `GEMINI_API_KEY` configured (also
matching a fresh clone: `.env.example`'s own `GEMINI_API_KEY=` is blank).
This is exactly the environment a judge's laptop would be in unless someone
hands them a working key. Asked all 6 starter questions from
`frontend/src/components/domain/AssistantPanel.tsx:35-44` verbatim, against a
freshly seeded backend:

| Scope | Question | Result |
|---|---|---|
| General | "why the Wilson lower bound instead of accuracy" | **Answered** (fell back to a cached recording) — genuinely good answer, cites ADR-0002/ADR-0007, uses concrete numbers (5/5 vs 384/400) |
| General | "what stops the LLM from raising a limit on its own" | **503 `assistant_unavailable`** — no matching recording |
| General | "where ground truth comes from in production" | **503 `assistant_unavailable`** — no matching recording |
| Agent (agent-01) | "why is this agent not eligible for an increase" | **503 `assistant_unavailable`** — no matching recording (one earlier attempt during this test also produced a raw, unformatted `Internal Server Error`, traced to a stale DB connection from my own Docker container restart mid-session, not an app bug — retried and got the clean 503 as expected) |
| Agent (agent-01) | "what would it take to reach the next rung" | **503 `assistant_unavailable`** — no matching recording |
| Agent (agent-01) | "explain this agent's most recent clawback" | **503 `assistant_unavailable`** — no matching recording |

**5 of the 6 built-in "Try Asking" starter questions fail outright, with a
raw error payload, in an unconfigured environment.** The one that worked did
so only because a recording happened to be cached from whatever
context/wording produced it during development; the other five recordings
that exist (3 general, 3 agent-scoped — visible in
`backend/app/data/assistant_recordings/`) simply don't correspond to the
current live evidence state or exact question wording, so the `live→cached`
fallback (`assistant_llm.py:126-147`) has nothing to fall back to. This is
the assistant feature's single biggest demo risk: the panel's own suggested
questions are the first thing a curious judge will click, and two-thirds of
them currently produce `{"code":"assistant_unavailable", ...}` rather than an
answer, unless whoever demos it either has a live `GEMINI_API_KEY` on the day
or re-records all 6 starters against the exact seed state that will be live
during the demo.

The good answer, in full, for the one working question:
> "Because raw accuracy can't tell a lucky streak from real evidence. Two
> agents at "100% accurate" and "96% accurate" sound like the first is
> better — but if the first is 5/5 and the second is 384/400, the Wilson
> lower bound (ADR-0002) puts the first at roughly 57% and the second at
> roughly 94%, and the ladder correctly reads the second as the stronger
> case... (System Explained, §3 Glossary; ADR-0002)."

This is genuinely strong answer quality — concrete numbers, correct
citations, on-topic — when it works. The problem is coverage, not quality.

---

## 4. The demo, run end to end

`scripts/demo.ps1 -NoPause` run twice, each with the script's own full reset
(drop the Postgres volume, recreate, migrate, seed, start a fresh backend on
port 8099, tear it down on exit).

| Beat | Run 1 | Run 2 | Match? |
|---|---|---|---|
| 1 (floor) | limit 2500, rung 2 | limit 2500, rung 2 | Identical |
| 2 (sim run) | 120 decisions, accuracy 94.2%, WLB 88.4% | Identical | Identical |
| 3 (trust eval) | accuracy 94.3% (n=122), WLB 88.6%, trust 84.9 | Identical | Identical |
| **4 (recommendation)** | **`direction=INCREASE status=PENDING has_dissent=False clamped=False`, 4/4 CONCUR** | **Identical** | **Yes — INCREASE with `has_dissent: false`, both runs** |
| 5 (approve) | `status=APPROVED` | Identical | Identical |
| **6 (limit after increase)** | **limit 5000, rung 3** | **limit 5000, rung 3** | Identical |
| 7 (inject critical error) | recorded | recorded | (decision id differs, expected) |
| 8 (drift) | CRITICAL, 1 error in window, recent 90.9% vs baseline 94.9% | Identical | Identical |
| **9 (clawback, before/after)** | **before 5000/rung3 → after 2500/rung2, no `/approve` call** | **Identical** | **Yes** |
| 10 (audit chain) | `chain_valid=True`, scope `full`, 143 entries | Identical | Identical |
| 10b (recovery, skipped by default) | not run | not run | n/a |

**Wall-clock:** run 1 = 18.9s, run 2 = 18.7s, both measured end to end
including the full Docker volume reset, migration, and seed. This is far
faster than the 8-Sept audit's own "~8 minutes"/"~6.5 minutes for beats 4-10"
figures — the backend's ingest path has clearly gotten faster since (batch
decision submission during a simulation run, not one HTTP round trip per
decision as some earlier manual testing used).

**Non-determinism:** only IDs (`run_id`, `decision_id`, `policy_version_id`)
differ between runs — every number, direction, status, and count is
byte-identical. The two runs are otherwise indistinguishable.

**I also ran `-WithRecovery` once**, to check §2b's newly-found double-clawback
risk against the actual beat 10b flow: recovery completed in 2.3s (105
decisions), returned `direction=INCREASE status=PENDING`, and the agent
recovered to limit 5000/rung 3 — no double-clawback this run, because the
fixed seed (100) for this recovery batch happens not to contain a critical
error within the drift window. This is exactly the fragility flagged in
§2b: it works today because of the seed choice, not because the code
prevents the failure mode. Also worth flagging on its own: `demo.ps1`'s own
comment (`scripts/demo.ps1:26-32`) says recovery costs "~105 sequential
decision submissions... several real minutes," citing the 8-Sept audit — that
figure is now **stale**; the real cost today is 2.3 seconds, a ~100x
improvement the comment doesn't reflect.

**Driving the same arc through the frontend UI, rather than the script:** the
`/demo` route (`frontend/src/app/demo/page.tsx`, added by PR #44) mirrors
`scripts/demo.ps1` beat-for-beat with a "RUN BEAT" / "NEXT" / "BACK" console
and a `LIVE`/`REPLAY` toggle — confirmed present and rendering correctly
against a live backend (§5). A presenter genuinely could drive the entire
ten-beat story from the browser without dropping to a terminal for the
happy path. Two exceptions, both edge cases rather than blockers: (1) the
optional beat 10b recovery run submits ~105 decisions and there is no
UI-visible progress indicator distinct from a plain loading state (the
script at least prints "Recovery run complete" with a timing line); (2) if
something goes wrong mid-arc (a stale recording, a database not freshly
reset), the UI has no equivalent of the script's `Reset-Environment` — a
presenter would still need a terminal to `docker compose down -v db` and
re-seed if the demo state gets into a bad condition on the day.

---

## 5. The frontend against a live backend

```
npm ci        → 472 packages, 0 errors; 4 vulnerabilities (3 high, 1 critical) — npm audit, not inspected further, flagged for the record
npm run typecheck → clean, no output
npm run build     → clean; Next.js 16.3.2, Turbopack; 8 routes: /, /_not-found,
                     /agents, /agents/[id], /approvals, /audit, /demo, /simulation
npm run lint      → 0 errors, 11 warnings (unused vars/imports, a handful of `any`)
```

**Boot against a live, freshly seeded backend, MSW off (the default).** First
attempt, using non-default ports (backend :8100, frontend :3100) to avoid
clashing with anything else running, produced every route stuck at a
permanent loading state with zero data — traced this to a real, concrete,
previously-unflagged finding, not a frontend bug: **`backend/app/main.py:35`
hardcodes `CORSMiddleware(allow_origins=["http://localhost:3000"])`** —
exactly one literal origin, no env var, no wildcard for dev. Any frontend
served from a different host or port (a different dev port, a deployed URL,
even `127.0.0.1:3000` instead of `localhost:3000`) is silently blocked by
CORS with no console error surfaced by the app itself (the browser's own
CORS rejection happens before the app's error handling ever sees it). This
is real and reproducible, not a one-off — PR #48 (§1) already fixes exactly
this ("CORS is configurable instead of hardcoded to localhost"), confirming
it's a known, named gap, not a surprise.

**Re-tested on the project's own documented default ports** (`backend`
Makefile target → port 8000; `npm run dev` → port 3000, matching
`api-client.ts`'s own fallback and `CORSMiddleware`'s literal allowlist) —
this is what a judge following the README/Makefile would actually run.
Every route rendered real, live data correctly, with **zero console errors**
and every API call returning `200`:

| Route | Renders | Evidence |
|---|---|---|
| `/` and `/agents` | Real data | `GET /agents` → 3 real agents, real limits (₹500/₹1,000/₹2,500), autonomy ladder with real current-rung marker |
| `/agents/agent-01` | Real data | Trust score 51.7, accuracy 100%, Wilson band "34–100%", drift/direction HOLD, full reason-code chips, governance trajectory chart with a real Wilson-band overlay, chronological policy-version history, recent decisions with ground truth |
| `/approvals` | Real data | A real pending `INCREASE` recommendation, `CLAMPED from ₹10k`, full panel rationale ("Panel: 4 concur, 0 object...") |
| `/audit` | Real data | "Hash Chain: Verified · Scope: full · 5 entries" — reading `chain_valid` from the API, not recomputing client-side |
| `/simulation` | Real data | Real agent dropdown (`agent-01 (Rung 2, ₹2,500)` etc.), phase/invoice-count controls |
| `/demo` | Real data | Ten-beat presenter console, beat 1 pre-populated with the real seed data |

Per demo beat, checked against a screenshot of the live-rendered page
(`/agents/agent-01`), not just the code:

| Beat capability | Shown? |
|---|---|
| Five-rung ladder, current position | **Yes** — real ladder component, current rung highlighted |
| Accuracy with a Wilson band that narrows | **Yes** — "Governance Trajectory" chart plots a real Wilson 95% band alongside the accuracy line and the limit step-chart |
| Drift status, recent vs. baseline | **Yes** — "Why autonomy changed" panel states the live reason codes and current gate status in full sentences |
| Four governance opinions, dissent surfaced | **Yes** — confirmed on `/approvals`, full per-agent panel text with concur/object counts |
| The clamp — `clamped`/`clamped_from` | **Yes** — "CLAMPED from ₹10k" rendered directly on the recommendation card |
| Audit chain verification reading real `chain_valid` | **Yes** — confirmed above |
| Autonomy over time, an increase and a clawback | **Yes**, component-level — the same trajectory chart plots policy-version history including past promotions; a clawback would render on the same chart (not independently re-triggered and re-screenshotted this round, but the chart reads real `policy_versions` data, not a fixture) |

**The hardcoded `0.85` threshold — confirmed still there, and visually
confirmed on screen, not just in code.** The live screenshot of
`/agents/agent-01` shows a "STATISTICAL EVIDENCE — Reliability Position"
panel presenting "**Threshold: 85%**" as a named, seemingly-authoritative
figure, and the trajectory chart draws a literal "Safety Threshold (85%)"
reference line — which visually **overlaps and collides with the chart's own
"100%" axis label** in the rendering I captured, a small but real visual
polish bug on top of the substantive one. Per the delegated pass's code
citation, `HorizontalThresholdGauge.tsx:12,17,21` still hardcodes
`threshold = 0.85` client-side, unfixed on `main` (only fixed in unmerged PR
#48). The real gate the system uses is `trust_score >= 70` (a different
metric on a different scale entirely) — so this panel is not just stale, it
is showing a number with no backend source at all, presented with the same
visual authority as the real Wilson-bound figures next to it.

---

## 6. Boundaries, tests, CI

*(Produced by the delegated research pass; the boundary-grep methodology and
per-lane test totals match my own independent runs of `backend/` and
`governance/` in §3.)*

**`shared/` freeze:** every branch and PR (including #48) diffed against
`main` for `shared/` only — every diff is empty. Unchanged since 2026-08-21.

**Boundary checks — real greps, current `main`:**

| Check | Result |
|---|---|
| `trust/` importing fastapi/sqlalchemy/psycopg/redis/celery/requests/httpx | Zero real hits |
| `trust/trust_engine/` file I/O, wall-clock reads, global mutable state | Zero hits |
| `governance/` importing sqlalchemy/psycopg/fastapi/backend.* | Zero hits |
| `backend/app/policy/` importing ORM/DB/network/LLM | Clean — only `shared.constants`, `shared.enums`, sibling modules, stdlib |
| `simulator/` importing backend code or touching the DB | Zero hits |
| Assistant feature (PR #45) location | Lives entirely inside `backend/` (`app/api/v1/assistant.py`, `app/services/assistant.py`, `app/services/assistant_llm.py`, `app/schemas/assistant.py`) — not a separate lane, no boundary violation |
| `frontend/` business logic | Two confirmed violations, both pre-existing, both unfixed on `main`, both fixed on unmerged PR #48: `HorizontalThresholdGauge.tsx:12,17,21` and `AutonomyTimeline.tsx:274,281` (a second, independent "Safety Threshold (85%)" hardcode) |
| `frontend/` hand-edited generated types | `frontend/src/types/generated.ts` — zero imports anywhere in `frontend/src`. Dead file, unchanged finding from every prior audit |

**Per-lane test counts, current `main` (`origin/main` @ `1819866`), each run separately:**

| Lane | Pass | Fail | Total |
|---|---:|---:|---:|
| `trust/` | 174 | 0 | 174 |
| `governance/` | 235 | 0 | 235 |
| `simulator/` | 123 | 0 | 123 |
| `backend/` | 249 | 0 | 249 |
| **Total** | **781** | **0** | **781** |

A combined `pytest` from repo root still fails on the `tests.conftest`
import-path collision, as every prior audit in this series found.

**CI:** `gh run list --branch main --limit 8` — all 8 most recent runs,
including the merge of `1819866`, show `success`. `simulator/` is genuinely
in CI now — `.github/workflows/ci.yml` runs ruff, `pytest simulator/tests`,
and a CLI reproducibility check (two `PYTHONHASHSEED`s, byte-diffed). This
closes the gap every prior audit (31-Aug, 06-Sept, 08-Sept) found open. **One
gap CI still has, not previously flagged this precisely:** `npm run lint` is
never run in CI — the frontend job runs only `typecheck` and `build`, despite
`frontend/package.json` defining a real `lint` script. Frontend lint status
has been invisible to CI at every audit checkpoint in this series.

**ruff, per lane, current `main`:** `trust/`, `governance/`, `simulator/`,
`backend/` — all four "All checks passed!"

**Reason codes — 17 of 18 reachable, not 16 and not 18.** This is a
correction to `docs/CONTEXT.md`'s current text (§7), which still says 16 of
18. Checked all 18 against every producer, not just consumers:

| Code | Reachable? | Producer |
|---|---|---|
| `INSUFFICIENT_SAMPLE`, `COOLDOWN_ACTIVE`, `TRUST_BELOW_THRESHOLD`, `AT_MAX_RUNG`, `DRIFT_ACTIVE`, `CLAWBACK_RECOVERY_PENDING`, `EVIDENCE_SUFFICIENT`, `NO_DRIFT_DETECTED`, `NO_RECENT_CRITICAL_ERRORS`, `COOLDOWN_SATISFIED` | Yes | `trust/trust_engine/ladder.py` |
| `CLAWBACK_DRIFT`, `CLAWBACK_CRITICAL_ERROR` | Yes | `trust/trust_engine/ladder.py:79,85`; applied via `backend/app/services/governance.py:203-224` |
| `NO_ACTED_DECISIONS`, `AGREEMENT_EVIDENCE_INSUFFICIENT`, `WEIGHTS_RENORMALISED` | Yes | `trust/trust_engine/score.py` |
| `RECOMMENDATION_CLAMPED` | Yes | `backend/app/services/governance.py:63,252` |
| `SAMPLE_REVIEW_DISAGREEMENT` | **Yes — newly closed by PR #43** | `backend/app/api/v1/audit.py:157` |
| `SAMPLE_EVIDENCE_INSUFFICIENT` | **No** | Only imported/checked in `governance/governance/agents/audit.py:22,34` (`EVIDENCE_GAP_CODES` tuple) — nothing anywhere, including inside PR #43's own new `audit_sampling.py`, ever appends it to a `TrustEvaluation`. Still true on unmerged PR #48 too. |

---

## 7. What would embarrass us

Ranked roughly by (severity if a panel finds it) × (how likely they are to
find it in three clicks or one obvious question).

### 1. `interactivehtml/index.html` — severely, publicly stale. High severity, ~1h to fix.

This is a standalone, publicly-reachable status page (not gated behind the
app) — exactly the kind of link a mentor or judge opens on their own device
before or after the live demo. Quoted directly, current file:

- `interactivehtml/index.html:305`, `:1305`: **"Status · 2 September 2026"**
  — twelve days stale as of today.
- `interactivehtml/index.html:245,1308`: **"Tests passing: 654"** — real
  total is **781** (§6).
- `interactivehtml/index.html:1309`: **"PRs merged, zero open — 26"** — real
  count is **48 merged, one open** (PR #48, §1). Both halves of this figure
  are wrong: more than name-doubled, and the "zero open" claim is false.
- `interactivehtml/index.html:1310`: **"Days to submission — 13"** — real
  number today is **1**. This is the single most jarring number on the page:
  a panel member doing arithmetic in their head ("13 days from when?") will
  notice instantly that the page was never touched since the second week of
  the project.

This page was already flagged as stale in the 08-Sept audit (then: 6 days
stale, "Tests passing: 654" already wrong then too). **It has not been
touched since, and the gap has only grown.**

### 2. `docs/DECISION_LOG.md` — 15 merged PRs, zero entries. Medium-high severity, ~2-3h to fix.

The standing rule (`docs/DEADLINES.md`: "One line in `docs/DECISION_LOG.md`
per merged PR") has not been followed since **2026-09-07**. `grep -n "PR #4"
docs/DECISION_LOG.md` matches nothing after PR #4 itself (a coincidental
substring match from 2026-08-23); the file's newest (top, reverse-chronological)
entry is dated 2026-09-07, for the cooldown-reset bugfix. **PRs #34 through
#48 — fifteen merged PRs spanning the entire clawback-auto-apply feature,
audit sampling, the demo script, the assistant chat feature, and the
clawback-trigger fix — have no log entry at all.** This is worse than every
prior audit's finding in this series (08-Sept: 6 unlogged; 06-Sept: 7
unlogged) — the gap has nearly tripled, not shrunk, going into freeze.

### 3. `docs/CONTEXT.md`'s own summary table is stale in the same ways its own audits found before. Medium severity, ~30min to fix.

- Backend row: **"212 tests"** → real is **249** (§3a, §6).
- "16 of the 18 codes... are reachable" → real is **17 of 18** (§6) — the
  document is now *more* pessimistic than reality on one code
  (`SAMPLE_REVIEW_DISAGREEMENT`, closed by PR #43) while still correctly
  flagging the other (`SAMPLE_EVIDENCE_INSUFFICIENT`, still open). This
  exact "stale count" failure mode — a fresh pass fixing four numbers, then
  new work landing that goes uncounted — is now visibly recurring across the
  06-Sept, 08-Sept, and this audit, each time in this same table.
- Neither ADR-0004 nor CONTEXT.md's beat 5 mention the §2b double-clawback
  finding — not a false claim (both are carefully, correctly scoped about
  what "automatic" means), just silent on a real gap discovered since they
  were last written.

### 4. The assistant's own suggested questions mostly fail. High severity if a judge tries them, ~2-4h to fix (re-record all 6 starters against the exact demo-day seed state, or ship a real `GEMINI_API_KEY` for the day).

Covered in full in §3e: 5 of 6 "Try Asking" starter buttons produce a raw
`assistant_unavailable` 503 in an environment with no live API key — which is
the default state of a judge's machine, and the default state of this
environment before I did anything. This is the single most likely
embarrassment in the entire review: the feature's own onboarding UI invites
exactly the click that breaks it two-thirds of the time.

### 5. The `0.85` threshold — a fabricated number presented with full visual authority. Medium severity (cosmetic, not a crash), ~1h to fix (already fixed on unmerged PR #48).

Covered in §5. Worth restating precisely because of how it reads on screen,
not just in a diff: a panel titled "STATISTICAL EVIDENCE — Reliability
Position" states "**Threshold: 85%**" next to real Wilson-bound numbers, with
no visual distinction between the real figure and the invented one. The
actual gate the system enforces is `trust_score >= 70` — a different metric,
a different scale, and a real backend value that this panel doesn't read.
Anyone technical in the audience who asks "why 85%, and why is that number
never mentioned anywhere else in the system" will get an answer nobody
prepared, because the honest answer is "it isn't real."

### 6. Backend CORS hardcoded to one literal origin. Low-medium severity (a documented, known gap; only bites on a non-default setup), ~30min to fix (already fixed on unmerged PR #48).

`backend/app/main.py:35`. Covered in §5. Low risk for the demo itself if run
exactly per the README/Makefile (`localhost:3000`/`localhost:8000`), but a
real, reproducible blocker for anyone deploying this anywhere else, or even
running the frontend on a different local port for a rehearsal.

### 7. The double-clawback / stale-evidence bug (§2b). Medium-high severity (silent, no error, wrong number on screen), ~2-4h to fix.

Not yet visible in the scripted demo (§4 confirms three clean runs), but
real, reproduced twice with different seeds, and newly *reachable
automatically* — with no human action — because of PR #47. If it fires
during a live, ad-libbed portion of the demo (a presenter running an extra
simulation batch to "show it again," or answering a judge's "what if I run
it once more"), the agent's limit will silently drop further than the
evidence justifies, with nothing on screen or in an error message
explaining why. This is exactly the kind of thing a panel might trigger by
asking to see the system do something slightly off-script.

### 8. Uncommitted, minor items — checked, nothing else rises to this level.

- No TODO/FIXME/commented-out block was found in any file a judge would
  plausibly open during a demo (checked `backend/app/api/v1/assistant.py`,
  `backend/app/services/{assistant,assistant_llm,governance,simulation}.py`,
  the frontend route files, `scripts/demo.ps1`) — the codebase's own
  documentation style (long docstrings explaining *why*, not commented-out
  dead code) makes this a non-issue here.
- No stub/placeholder is presented in the UI as if it were real, beyond the
  `0.85` threshold above — every other panel checked in §5 reads a genuine
  backend value.
- No crash or empty state was found within three clicks of the landing page
  on the documented default ports (§5) — every route rendered real data
  cleanly. (It *did* fail completely on non-default ports, but that's a
  configuration mismatch a presenter following the README won't hit, not a
  "three clicks from landing" risk.)
- Nothing non-deterministic or timing-dependent was found in the scripted
  demo path itself (§4) beyond IDs — the one non-determinism that matters
  (§2b/§7.7) is a *risk in code paths adjacent to* the demo script, not
  inside it as currently written.

---

## 8. Per-person status

Paste-ready, no editing needed.

### Varun P. (backend, lead)

**Finished:** the clawback-trigger fix (PR #47) is live-verified end to end —
a degrading simulation run now auto-applies a clawback with zero manual
calls, exactly as claimed, and the pre-existing manual path and
cascade-guard-for-repeated-no-new-evidence case both still work correctly.
Backend is at 249 passing tests, ruff-clean, and is the only lane whose CI
coverage gap (simulator) has been fully closed by someone else's work this
window.

**Outstanding:**
1. Fix the double-clawback bug found in §2b: the cascade guard
   (`backend/app/services/governance.py:159`) checks
   `decisions_since_last_change == 0`, but drift is computed over a rolling
   20-decision window (`CRITICAL_ERROR_WINDOW`, `trust/trust_engine/constants.py:30`)
   — the guard needs to key off whether the *specific* critical
   error/drift evidence that justified the last clawback is still the one
   being cited, not whether any new decision exists at all. **~3-4h**
   (diagnosis is done; this report has the exact repro).
2. Merge PR #48 (`uk/integration-dryrun`) — reviewed and independently
   verified in §1: zero conflicts, 882 tests passing, ruff-clean, closes the
   CORS hardcode, the 0.85 threshold, the stale-rung-jump gap, and hands the
   team a written `docs/DEPLOYMENT.md` for free. **~1-2h** (review + merge,
   not new implementation).
3. Backfill 15 missing `DECISION_LOG.md` entries (PRs #34-#48). **~2-3h.**
4. Update `docs/CONTEXT.md`'s backend test count (212→249 or whatever the
   post-merge-#48 number is) and the reason-code count (16/18→17/18). **~20min.**
5. Update `interactivehtml/index.html`'s entire status section — date, test
   count, PR count (48 merged, and whether #48 is merged or still open by
   submission), days-to-submission. **~1h.**

**Total: ~7-11h.**

### Utkarsh (trust, simulator, and PR #48)

**Finished:** PR #48 is fully built, tested (882 tests including 249→323
backend growth on that branch), ruff-clean, and already reconciled by hand
against PR #47's independent fix for the same underlying gap (merge commit
`9e4bb89`) — including going further than #47 by also auto-generating
INCREASE recommendations at the end of a good run, closing the other half of
ADR-0004's asymmetry that #47 alone left unaddressed. Trust engine remains
complete and untouched (174/174).

**Outstanding:**
1. Get PR #48 in front of Varun P. for review/merge — it's finished. **~0h
   new work, ~15min to ping.**
2. `SAMPLE_EVIDENCE_INSUFFICIENT` is still not emitted anywhere, including in
   this branch — if closing all 18 reason codes before submission matters,
   this needs a producer somewhere in `trust/trust_engine/score.py` or the
   audit-sampling evaluation path. **~2-3h if pursued; not blocking anything
   else.**

**Total: ~2-3h, all of it optional.**

### Varun C. (governance)

**Finished:** nothing outstanding found in this audit for this lane —
235/235 tests, ruff-clean, no boundary violations, `generate_text()` addition
(needed by the assistant feature, §3b) verified additive with zero change to
the four governance agents' own behavior.

**Outstanding:** none found. If time allows, the assistant's cached
recordings (`backend/app/data/assistant_recordings/`, a backend-owned
directory but the same recording-store code Varun C. built for governance)
are the fastest fix for §7.4 — recording all 6 starter questions against the
exact seed state that will be live on demo day would need only
`python -m governance.record` pointed at the assistant's namespace, per the
error messages `assistant_llm.py` already prints when a recording is
missing. **~1-2h**, cross-lane but mechanically simple, worth naming as a
shared task rather than solely Varun P.'s.

**Total: 0h required, ~1-2h optional and high-value.**

### Adhya (frontend)

**Finished:** typecheck, build, and lint all clean; 8 routes build cleanly;
every route verified live, rendering real data with zero console errors, on
the project's documented default ports. The `/demo` presenter console (PR
#44) genuinely lets a presenter drive the full ten-beat arc from the browser.

**Outstanding:**
1. Wire `HorizontalThresholdGauge`'s `isHealthy` prop and
   `AutonomyTimeline`'s "Safety Threshold (85%)" line to a real backend
   value instead of the hardcoded `0.85` — **already done on unmerged PR
   #48** (adds a real `thresholds` field to `TrustEvaluationOut`); this is
   now a merge-and-verify task, not new frontend work. **~30min to confirm
   after PR #48 lands.**
2. The visual collision between the "Safety Threshold (85%)" line label and
   the chart's own "100%" axis label (visible in a live screenshot taken for
   this audit) will likely resolve itself once (1) removes the fake
   threshold line entirely — worth a quick visual re-check either way.
   **~15min.**
3. `frontend/src/types/generated.ts` — still dead, zero imports, unchanged
   finding from every audit in this series. Either delete it and the unused
   `gen:api` script, or leave it and stop flagging it — it is not causing
   any functional problem, only repo hygiene. **~15min to delete.**

**Total: ~1h**, smallest outstanding load of the four, and most of it is
"confirm someone else's fix landed" rather than new work.

### Non-code deliverables — what's already covered in the repo

- **Deployment strategy documentation:** not written yet on `main`, but
  **`docs/DEPLOYMENT.md` and `render.yaml` already exist, finished, on
  unmerged PR #48** — merging #48 produces this deliverable as a side
  effect, not from scratch. `docs/adr/0008-monolith-over-microservices-for-prototype-scope.md`
  is also directly reusable: it already argues the "why one deployable unit,
  not four services" question a deployment section would need to answer,
  with real consequences and alternatives-considered sections.
- **Future scope:** no dedicated document exists, but `docs/CONTEXT.md:247-260`'s
  "Explicit non-goals" section is a ready-made inverse of a future-scope
  list — real bank/ERP integration, production-grade auth beyond the current
  RBAC scaffold, general document understanding, multi-tenant/HA support,
  and generalizing beyond invoice approval are all already named as
  deliberately out of scope, with the reasoning already written. Flipping
  this list into "what's next" framing is an editing task, not a research one.
- **Presentation storyboard:** nothing in the repo covers this directly, but
  `docs/CONTEXT.md`'s "The demo script" section (the ten numbered beats,
  each with its current real/stubbed status) and `scripts/demo.ps1`'s own
  beat captions (`Write-Caption` strings, one per beat, already written as
  presenter-facing narration) are the closest existing material — a
  storyboard could be built by lifting these captions directly rather than
  drafting narration from scratch.

---

## 9. Three days out

**If the demo were tomorrow, on the documented default setup:** it would
show exactly what §4 and §5 confirm — a live-earned INCREASE with no dissent,
a real human approval, the limit visibly rising, a real critical error
triggering CRITICAL drift, an automatic clawback with zero approval clicks,
and a verified hash chain, all driven through the real API, deterministically,
in under 20 seconds, either from the terminal or from the browser's own
`/demo` console. **What would visibly be missing or broken:** two of the
three assistant starter buttons in *any* scope produce a raw error rather
than an answer unless someone has a live Gemini key that day (§3e/§7.4); the
"Reliability Position" panel's 85% threshold is a number the system doesn't
actually use (§5/§7.5); and `interactivehtml/index.html`, if anyone opens it,
visibly contradicts the demo they just watched by six weeks of stale numbers
(§7.1).

**The three highest-value fixes in the next 24 hours, in order:**

1. **Re-record the assistant's 6 starter questions** against the exact seed
   state that will be live on demo day (§3e/§7.4). This is the single most
   likely thing a curious panel member will personally trigger, it currently
   fails 5/6 of the time, and the fix is mechanical (run
   `python -m governance.record` once per starter, in both scopes) rather
   than a design decision — **~2h, and it's the highest-leverage fix on this
   list because it's the one a judge is most likely to personally click.**
2. **Merge PR #48** (§1, §8). Zero conflicts, already tested at 882 passing,
   and it closes three separate items from §7 in one merge: the CORS
   hardcode, the fake 0.85 threshold, and the stale-rung-jump approval gap —
   plus it produces `docs/DEPLOYMENT.md` as a free non-code deliverable.
   **~1-2h of review, not new work.**
3. **Fix the double-clawback cascade guard** (§2b, §8 item 1 for Varun P.).
   Not visible in the scripted demo today, but it is a real, silent,
   automatically-triggerable bug with no error message, sitting directly
   behind the exact "run it again" ad-lib a panel might ask for. **~3-4h.**

**Update the two stale-docs items** (`docs/CONTEXT.md`'s count table,
`interactivehtml/index.html`'s whole status section, `docs/DECISION_LOG.md`'s
backfill) **only after** the above — they're real findings (§7.1-7.3) but
none of them can make the demo itself fail; they can only embarrass the team
if a panel member goes looking at the docs independently, which is a real
but lower-probability risk than the three items above.

**Is there anything that should be removed rather than fixed?** No. Nothing
found in this audit is weaker than its own absence would be. The assistant
chat feature is the closest candidate — a feature whose own suggested
entry points mostly fail is a real risk — but the underlying capability
(isolation holds, answer quality is genuinely good when it works, the
architecture is sound) is worth the ~2 hours it costs to fix properly rather
than worth hiding three days before submission. Cutting it now would remove
a feature that works and replace it with an unexplained gap in "what does
this system do" for no time saved over just recording the six answers.
