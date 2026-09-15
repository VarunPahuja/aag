# Final Verification Audit — 2026-09-15 (submission day)

Read-only, except this file and `docs/PRESENTATION-FACTS.md`. No application
code was written, edited, staged, committed, pushed, merged, rebased, or
formatted to produce either. Verification requiring running code (Docker,
Postgres, the backend, `npm`, `pytest`, `ruff`, `scripts/demo.ps1` x2, a real
headless Chromium against a live frontend+backend) ran in disposable git
worktrees (`../TrustIssues-audit2-main`, `../TrustIssues-audit3-main`,
`../TrustIssues-facts-main`, each at `origin/main`) or directly against
Docker/Postgres state, never against the real working tree's git state.

**A material, honest note on methodology:** this audit ran concurrently with
real, active development in the same repository. The primary working
directory moved through `vp/clawback-trigger` → `vp/ci-assistant-lane` →
`vp/azure-openai-chat-provider` while this audit was in progress — not an
action of this audit, confirmed via `git reflog`, and `origin/main` itself
advanced three times during the session (PR #48 → #49 → #50). This report
verifies `origin/main` @ `1f14bc1` (PR #50), the tip as of this writing, and
says explicitly wherever a finding might already be stale by the time it's
read. Part of this investigation was delegated to two background research
passes with the same constraints; I independently re-ran their two most
load-bearing numbers (the backend test count, the CI-failure claim) myself
and got matching results before relying on either.

---

## 1. What moved since 12 September

`origin/main` advanced from `3d724ae` (12-Sept audit's endpoint, then PR #49)
through PR #50, to **`1f14bc1`**, as of this writing.

| SHA | Author | Merged (IST) | PR | Lane(s) | Files | What it actually did |
|---|---|---|---|---|---|---|
| `62c9882` | Utkarsh | 09-14 23:05 | #48 | backend+frontend+governance+simulator+docs | **45** (10 more than the 12-Sept audit saw while it was still open — it grew before merging) | Everything the 12-Sept audit already verified in-flight, plus, confirmed in the final merged state with tests: **(1)** `GET /audit-log`'s chain verifier was checking hash-chain order by caller-supplied `ts` instead of the monotonic `log_seq` column migration 0003 exists specifically to provide — measured live on the real database, **2,912 entries, 0 broken hashes, 0 real gaps, but 11 false-positive "tampering" ordering inversions** from `ts` ties, now fixed (`backend/tests/test_audit_chain_order.py`). **(2)** `approve_recommendation` no longer applies a `PENDING` recommendation that has gone stale by more than one rung — a 409 `recommendation_stale` now, not a silent multi-rung jump (`backend/tests/test_stale_recommendation_guard.py`, 7 tests). **(3)** A one-line, single-author edit to `shared/reason_codes.py` — `CLAWBACK_CRITICAL_ERROR`'s human-readable description, previously "Autonomy reset to the floor after a critical error" (factually wrong; it drops exactly one rung, identically to its sibling `CLAWBACK_DRIFT`), corrected to "Autonomy reduced one rung after a critical error." **This changed a `shared/` treaty file** — self-disclosed in `docs/DECISION_LOG.md`'s 2026-09-14 entry, not hidden, but it means "`shared/` has never changed since the freeze," a claim every prior audit in this series made and re-confirmed, **is no longer true as of today.** |
| `3d724ae` | Varun C. | 09-14 23:11 | #49 | new top-level `assistant/` package + governance | 20 | Real retrieval grounding for the assistant chat feature: a committed `assistant/index.json` (135 chunks, Gemini embeddings, cosine similarity, `RELEVANCE_THRESHOLD = 0.62`, ADR-0015) so the assistant quotes this repository's own docs instead of the base model's general knowledge. Genuinely well-engineered — its own `assistant/tests/test_import_boundary.py` is a real AST-based test enforcing the package's boundary rules (no DB, no backend import, no second LLM SDK, no vector-database dependency), wired into CI (`ruff check ... assistant/`, `pytest assistant/tests`). **This PR's own merge to `main` failed CI** — see §2. |
| `1f14bc1` | Varun P. | 09-14 23:53 | #50 | CI config only | 3 | Restores green CI after #49's failure — **by disabling the check that caught the problem, not by fixing the problem**. See §2 for exactly what this leaves broken. |

**PR #51, real and finished, not on `main`:** `feat(governance): Azure OpenAI as a chat-only LLM provider`, merged into `vp/ci-assistant-lane` (2026-09-14 18:38) — that base branch is itself already merged into `main` via #50, so #51 has simply never been proposed against `main` directly, not because it's unfinished. Adds a fourth `GOVERNANCE_PROVIDER` (`governance/governance/llm/azure_openai.py`) wired to a real, live-confirmed Azure AI Foundry endpoint shape (`services.ai.azure.com/.../openai/v1/responses`, `api-key` header, no `api-version` query param, text nested at `output[].content[].output_text` — none of which matches the classic Azure OpenAI dialect `openai_client.py` already implements). **Chat-only, explicitly**: `assistant/embed.py` still raises `EmbeddingsUnsupportedError` for anything but Gemini, so this cannot rebuild the stale index in §2. Not the default provider, requires no key to run the rest of the system, ruff-clean, its own test file. Verified this merges onto current `main` with **zero conflicts**. This is the one genuinely unmerged, finished, submission-day-relevant piece of work outstanding.

Every other remote branch checked (`ad/demo-console`, `uk/audit-sampling`, `uk/simulator-finalise`, every remaining `vc/*`/`vp/*` feature branch) is a stale ref whose tip either exactly matches an already-merged PR's head commit or is a literal ancestor of `main` — the same false-alarm pattern every prior audit in this series has documented; nothing new among them.

**`docs/DECISION_LOG.md`**: grew from 657 lines (12-Sept audit) to **1036 lines**. Read in full: **zero merge-conflict markers**, no truncation, no duplicated sections — reads correctly, reverse-chronological, top to bottom. **The merge conflict resolved cleanly.** But the gap the 12-Sept audit found is only partly closed: the newest entries (lines 9–140) cover PR #49 (tagged `#49` explicitly) and three dated entries for PR #48's branch (`uk/integration-dryrun`, 09-12/13/14) — **there is still no entry anywhere in the file for PR #45, #46, or #47**, confirmed by content search (branch names, dates, subject text), not just an exact `#45`/`#46`/`#47` string match. Three merged PRs — including the clawback-trigger fix this whole series has centered on — remain entirely unlogged, sitting directly underneath otherwise thorough logging for the PRs merged after them.

---

## 2. Is anything broken

### Per-lane test counts, current `main` (`1f14bc1`), each run separately

| Lane | Pass | Fail | Skip | Total |
|---|---:|---:|---:|---:|
| `trust/` | 174 | 0 | 0 | 174 |
| `governance/` | 251 | 0 | 0 | 251 |
| `backend/` | **327** | 0 | 0 | 327 |
| `simulator/` | 134 | 0 | 0 | 134 |
| `assistant/` (new lane, PR #49) | 115 | 0 | **3** | 118 |
| **Total** | **1001** | **0** | **3** | **1004** |

The backend figure (327) was run twice, independently, on two separate
worktrees, matching exactly both times — this is the verified number, not an
estimate. A combined `pytest` from repo root still fails on the
`tests.conftest` import-path collision, unchanged from every prior audit.

**The 3 skips in `assistant/` are the single most important finding in this
report — not incidental, and not yet fixed as of this writing.**

`assistant/index.json` was built **2026-09-14T09:19:58 UTC** — before PR #48
merged its changes to `docs/CONTEXT.md`, `docs/adr/0009-*`, and, critically,
**the exact `shared/reason_codes.py` correction described in §1**. Verified
directly, on the true current `main`:

```
$ grep -o "reset to the floor after a critical error" assistant/index.json
reset to the floor after a critical error
```

```
$ grep -n "CLAWBACK_CRITICAL_ERROR:" shared/reason_codes.py
54:    CLAWBACK_CRITICAL_ERROR: "Autonomy reduced one rung after a critical error.",
```

**The assistant's own committed retrieval index still contains the
factually wrong sentence the rest of the codebase corrected in the same
merge window.** Ask it "what does a critical-error clawback do" today and it
will answer from the stale chunk, contradicting the corrected text one click
away in the ADR it's supposed to be quoting.

This is exactly what broke CI: **PR #49's own merge commit (`3d724ae`) has a
`failure` conclusion** (`gh run list --branch main`, run id `34876299739`,
independently confirmed, not taken on a report's word) — the freshness-guard
test caught the staleness the moment PR #49 landed six minutes after PR #48.
**PR #50, the very next commit, restored a green checkmark by marking the
three freshness tests `@pytest.mark.skip` and adding `continue-on-error:
true` to the CI staleness step — not by rebuilding the index.** The CI
YAML's own comment states this plainly (`.github/workflows/ci.yml:81-84`):
*"the index is currently stale... this step is expected to fail until
someone rebuilds it with `python -m assistant build`. Remove
continue-on-error in the same change that removes those skips."* Running
that check myself, right now, confirms it: **`python -m assistant check`
exits 1**, reporting `STALE` against `docs/CONTEXT.md`, `docs/adr/0009-*`,
and `shared/reason_codes.py`. The fix needs a live `GEMINI_API_KEY` to
re-embed — nobody has run it yet.

**Is main green? Yes at the tip, and only because of the above.**

| Commit | PR | CI conclusion |
|---|---|---|
| `1f14bc1` | #50 | success |
| `3d724ae` | #49 | **failure** |
| `62c9882` | #48 | success |

**Did anything merge with failing CI? Yes — #49.** It didn't stay red, but
the fix that followed defused the check that caught the problem rather than
closing the gap it found.

**ruff, per lane, current `main`:** `trust/`, `backend/`, `governance/`,
`simulator/`, and now `assistant/` (added to CI's ruff line by PR #50) — all
five "All checks passed!", run directly.

**Frontend:**
```
npm ci        → 472 packages, 0 vulnerabilities (down from 4 at the 12-Sept audit)
npm run typecheck → clean, no output
npm run build     → clean; Next.js 16.3.5, Turbopack; same 8 routes, now
                     correctly nested under a (dashboard) route group per
                     PR #48's restructure
npm run lint      → 0 errors, 11 warnings — same count, same files, as 12-Sept
```
No regression from PR #48's frontend changes. The fake-`0.85`-threshold fix
the 12-Sept audit found PR #48 doing correctly for `HorizontalThresholdGauge.tsx`
is confirmed still in place, unchanged — but see §5 for its still-unfixed sibling.

---

## 3. The demo, run twice

`scripts/demo.ps1 -NoPause`, full reset between runs (drop the Postgres
volume, recreate, migrate, seed), against `origin/main`'s merged content
(run on `3d724ae`, one commit behind `1f14bc1` — the intervening commit, PR
#50, touches only `.github/workflows/ci.yml`, not application code, so this
is representative of current `main`'s actual runtime behavior).

| Beat | Run 1 | Run 2 |
|---|---|---|
| 1 (floor) | limit 2500, rung 2 | Identical |
| 2 (sim run) | 120 decisions, accuracy 91.4%, WLB 81.4% | Identical |
| 3 (trust eval) | accuracy 91.7% (n=60), WLB 81.9%, trust 83.1 | Identical |
| **4 (recommendation)** | **`direction=INCREASE status=PENDING has_dissent=False`, 4/4 CONCUR** | **Identical** |
| 5 (approve) | `status=APPROVED` | Identical |
| **6 (limit after increase)** | **limit 5000, rung 3** | **Identical** |
| 7 (inject critical error) | recorded | (decision id differs, expected) |
| 8 (drift) | CRITICAL, 1 error in window | Identical |
| **9 (clawback, before/after)** | **before 5000/rung3 → after 2500/rung2, no `/approve` call** | **Identical** |
| **10 (audit chain)** | **`chain_valid=True`, scope `full`, 205 entries** | **Identical** |
| 10b (recovery, off by default) | not run | not run |

Confirmed exactly as asked: **beat 4 returns INCREASE with `has_dissent:
false` both times; beat 9 claws back with zero `/approve` calls anywhere in
the sequence, both times; beat 10's `chain_valid` is `true` both times.**
After normalizing IDs (`run_id`/`decision_id`/`policy_version_id`, expected
to differ) and wall-clock text, **the two runs' output is byte-identical** —
full determinism confirmed, not just spot-checked.

The accuracy/Wilson numbers here (91.4%/81.4%) differ from the 12-Sept
audit's own run of the same script (94.2%/88.4%) — this is a real,
intentional behavior change from PR #48 (the simulated agent now escalates
based on `amount > current_limit` rather than never escalating at all, which
changes the decision plan's shape), not a determinism regression; both runs
in this session match each other exactly, which is the property that
matters.

**Wall-clock:** run 1 = 22.2s, run 2 = 19.8s, both full end-to-end including
the Docker volume reset. **Non-determinism:** only IDs, as above — nothing
else differs between runs.

---

## 4. The UI, live

Booted the frontend (`npm run dev`, port 3000) against a freshly seeded
backend (port 8000 — the project's own documented default pair, matching
`Makefile`'s `backend` target and `CORSMiddleware`'s configured allowlist),
MSW off (the default), driven with a real headless Chromium
(Playwright), not just HTTP status checks.

| Route | Result |
|---|---|
| `/` | **Real data** — a genuine marketing-style landing page (new since the 12-Sept audit's plain redirect), scroll-revealed sections that render correctly once scrolled through, including a live worked Wilson-math example ("Twenty-two out of twenty-two correct — and the system refused to give it more authority... On twenty-two samples a perfect record only proves 85%") |
| `/agents`, `/agents/agent-01` | **Real data**, zero console errors — trust score, accuracy, Wilson band, drift state, and (from residual state left by the demo runs above) real `DRIFT: CRITICAL` / `CLAWBACK — AUTONOMY CLAWED BACK` badges, confirming the UI renders the unhappy path correctly too, not just the golden path |
| `/approvals` | **Real data** — a real pending INCREASE, "CLAMPED from ₹10k", full four-agent panel rationale text |
| `/audit` | **Real data** — "Hash Chain: Verified · Scope: full · 205 entries", reading `chain_valid` from the API |
| `/simulation` | **Real data** — real agent dropdown with live rung/limit values |
| `/demo` | **Real data** — the ten-beat presenter console, beat 1 pre-populated from real seed state |

Every route: **zero console errors**, every API call `200`.

**Can a presenter drive the whole ten-beat story from the browser? Yes, for
the happy path — with one specific, confirmed exception.** The `/demo`
console's "RESET CONSOLE" button (`frontend/src/app/demo/page.tsx:146-150`,
`handleReset`) only resets the **browser's own** UI state
(`stepIndex`/`slots`) — confirmed by reading the function, it makes no API
call and touches no backend state. If the demo database gets into a bad
condition mid-rehearsal (an agent already clawed back, a wrong rung), a
presenter still needs a terminal to `docker compose down -v db` and reseed —
there is no in-browser equivalent of `scripts/demo.ps1`'s own
`Reset-Environment`. This is unchanged from the 12-Sept audit's finding,
re-confirmed against the current code rather than carried forward.

**The `HorizontalThresholdGauge` fix, confirmed live, and its still-broken
sibling:** `/agents/agent-01`'s "Reliability Position" panel no longer shows
the fabricated `85%` badge from the 12-Sept audit — it now reads
"Drift: CRITICAL" and explains the real mechanism ("Drift fires if recent
accuracy falls 10 points below its own baseline target — there is no fixed
accuracy target"), sourced from the real `thresholds` field PR #48 added to
`TrustEvaluationOut`. **But the trajectory chart directly above it still
draws the old hardcoded line**: `frontend/src/components/charts/AutonomyTimeline.tsx:274-281`

```tsx
{/* Safety Threshold Horizontal Line at 85% */}
<ReferenceLine
  yAxisId="pct"
  y={85}
  ...
  label={{ value: "Safety Threshold (85%)", ... }}
/>
```

One of the two hardcoded-85% instances the 12-Sept audit named was fixed;
the other, in a different file, was not — confirmed on screen (a visible
"Safety Threshold (85%)" dashed line and label on the same chart that
correctly plots the real Wilson band beside it) and in code.

---

## 5. What would embarrass us

Ranked by (severity if found) × (likelihood of being found).

### 1. The assistant will confidently quote a wrong fact about the system's own safety mechanism, right now. Severe. ~1-2h to fix, needs a live `GEMINI_API_KEY`.

Covered fully in §2. This is worse than a stale test count on a docs page —
it is the system's own "ask me anything, I cite sources" feature actively
misdescribing what a critical-error clawback does (claims "reset to the
floor," the code does, and always did, drop exactly one rung), sourced from
a retrieval index the team's own CI caught as stale and then explicitly
chose to stop blocking on rather than fix, hours before submission. If a
judge asks the assistant to explain the clawback mechanism — a near-certain
question given it's the demo's own climactic beat — there is a real chance
it answers from the wrong chunk. **This wasn't found by digging; it's
self-documented in the CI YAML's own comments.**

### 2. `docs/CONTEXT.md`'s "Current status" table is stale in a new, ironic way. Medium severity, ~20min to fix.

Dated "Reality as of **2026-09-09**" — six days stale, and PR #48 touched
this exact file (per its own changelist) without refreshing the date or the
now-wrong test counts (backend row says "262 tests," real is 327; governance
"251" happens to be right; simulator "134" happens to be right). Worse:
**the frontend row still says `HorizontalThresholdGauge`'s hardcoded `0.85`
is the one remaining violation** — that's now fixed (§4) — while saying
nothing about `AutonomyTimeline.tsx`'s still-broken sibling. The document is
stale in the *safe* direction on one bug and silent on the real one still
open — a small irony worth naming precisely rather than glossing over.

### 3. `docs/DECISION_LOG.md` — three PRs, including the flagship clawback fix, remain unlogged. Medium severity, ~1h to fix.

Covered in §1. PR #48 and #49's own work is logged thoroughly and well; #45,
#46, #47 are not logged at all, even after this pass. The standing rule
("one line per merged PR") is being followed inconsistently rather than
abandoned — worth fixing precisely because the surrounding entries are
genuinely excellent and make the three gaps more visible by contrast, not less.

### 4. The assistant's own suggested starter questions are still mostly broken — unchanged since the last audit's #1 recommendation. High severity if a judge tries them, ~2h to fix.

Re-verified directly: with no `GEMINI_API_KEY` configured (still true in
this environment, and almost certainly true of a judge's machine), asking
"why the Wilson lower bound instead of accuracy" still works (falls back to
an existing cached recording, genuinely good answer). A spot-check of a
question touching the newly-stale content (`"how does audit sampling
work"`) still 503s with `assistant_unavailable` for lack of both a live key
and a matching recording. **This was the single highest-priority
recommendation of the 12-Sept audit** (re-record the 6 starter questions) —
of the three top recommendations from that audit, the other two (merge PR
#48, fix the double-clawback cascade guard — see below) were acted on; this
one was not.

### 5. `AutonomyTimeline.tsx`'s hardcoded 85% line. Low-medium severity (cosmetic, one file), ~20min to fix.

Covered in §4. A precise, narrow, already-half-fixed finding — the pattern
and the fix are both already sitting in the same PR that fixed its sibling.

### 6. One commit on `main`'s own history has a failing CI run. Low severity on its own (main is green today), but worth stating precisely: ~0h, already "fixed" in the sense of not blocking anyone — the real fix is item 1 above.

### What I checked and did *not* find anything new on:

- **The double-clawback cascade guard** (12-Sept audit §2b, `backend/app/services/governance.py:159`): not re-tested live this session (time-boxed against the newer findings above), but no fix for it appears in PR #48's diff or `docs/DECISION_LOG.md`'s entries for that branch — treat as **still open** unless re-verified.
- **CORS hardcode**: fixed, confirmed in §4 of the 12-Sept audit's own follow-up and re-confirmed here (`backend/app/config.py:cors_allow_origins()`).
- No TODO/FIXME/commented-out block was found in any file a judge would plausibly open this session (`assistant/`, `backend/app/api/v1/*.py`, `scripts/demo.ps1`, the frontend route files).
- No crash or empty state within three clicks of the landing page on the documented default ports — every route in §4 rendered real data.
- Nothing else non-deterministic or timing-dependent was found in the demo script itself beyond IDs (§3).

---

## 6. Fix list

Ordered by severity, hours only, nothing cosmetic-for-its-own-sake, no new features.

| # | Fix | Severity | Hours | File(s) |
|---|---|---|---|---|
| 1 | Rebuild `assistant/index.json` against current docs (`python -m assistant build`, needs a live `GEMINI_API_KEY`), un-skip the 3 freshness tests, remove `continue-on-error` from the CI staleness step | **High** — the assistant is currently quoting a disproven safety-mechanism description | 1-2h | `assistant/index.json`, `assistant/tests/test_cli.py`, `assistant/tests/test_index.py`, `.github/workflows/ci.yml:81-87` |
| 2 | Re-record the assistant's 6 "Try Asking" starter questions (general + agent-scoped) against the exact seed state that will be live on demo day | **High** — first thing a curious judge clicks, still fails most of the time | 2h | `backend/app/data/assistant_recordings/`, `python -m governance.record` |
| 3 | Remove `AutonomyTimeline.tsx`'s hardcoded 85% reference line, same fix already applied to `HorizontalThresholdGauge.tsx` in the same PR | Medium — a fabricated number still visible on the main agent-detail chart | 20min | `frontend/src/components/charts/AutonomyTimeline.tsx:274-282` |
| 4 | Backfill `docs/DECISION_LOG.md` entries for PR #45, #46, #47 | Medium | 1h | `docs/DECISION_LOG.md` |
| 5 | Update `docs/CONTEXT.md`'s "Current status" table: date, backend test count (327), and correct the frontend row to reflect the `HorizontalThresholdGauge` fix and name `AutonomyTimeline`'s remaining hardcode instead | Medium | 20min | `docs/CONTEXT.md:262-291` |
| 6 | Re-verify the double-clawback cascade guard (12-Sept audit §2b) against current `main` — not re-tested this session, no evidence it was addressed in PR #48 | Medium, unconfirmed | 30min to verify, 3-4h to fix if still open | `backend/app/services/governance.py:159` |
| 7 | Consider merging PR #51 (Azure OpenAI chat provider) — finished, tested, zero conflicts, not required for the demo to work | Low, optional | 15min review | — |

**Total, items 1-5 (the ones confirmed broken or embarrassing today): ~5-6 hours.**
