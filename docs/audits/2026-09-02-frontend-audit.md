# Frontend Audit — 2026-09-02

Read-only. Nothing in this repository was written, edited, staged, committed,
or pushed to produce this report except this file itself. Verification
(`npm install`/`typecheck`/`build`/`lint`, a full `docker compose` → `alembic`
→ seed → `uvicorn` → `next dev` live run) was run against processes only —
no tracked file was touched, and both servers were killed afterward.

Baseline: `docs/audits/2026-08-31-state-audit.md` §3 (frontend-specific
checks, lines 327–341) and its vertical-slice hop 9 finding. Also read:
`docs/lanes/ad.md`, `backend/openapi.json`, `shared/contracts.py`,
`shared/constants.py`, `shared/enums.py`, `shared/reason_codes.py`.

Working tree: `main` at `8496b2491464c75d51b27732fee82ec6b0955940`.

---

## 1. What landed

One squash-merged commit carries everything since 27 Aug:

| | |
|---|---|
| SHA | `8496b2491464c75d51b27732fee82ec6b0955940` |
| Author | Adhya Sharma `<adhyasharma1806@gmail.com>` |
| Date | 2026-09-02 22:47:45 +0530 |
| PR | #27, merged 2026-09-02T17:17:46Z |
| Subject | `feat(frontend): port dashboard onto v1.1 contracts and 5-rung ladder (#27)` |

`git log --since=2026-08-27 --oneline -- frontend/` returns exactly this one
commit — no other commit touched `frontend/` in the window. Same for
`simulator/`.

**31 files changed, 6,710 insertions(+), 5,391 deletions(-)** (`git show
--stat 8496b24`), split:

- **`frontend/`: +3,761 / −990**, 20 files — `package.json`,
  `package-lock.json`, five `app/**/page.tsx` route files, `globals.css`,
  three chart/domain components rewritten, two components deleted
  (`AccuracyGauge.tsx`, `ApprovalRow.tsx`), `lib/api-client.ts`,
  `mocks/data.ts`, `mocks/handlers.ts`, `types/api.ts` rewritten, and a new
  `types/generated.ts`.
- **`simulator/`: +2,949 / −4,401**, 11 files — `api_client.py`,
  `labeller.py`, `runner.py`, `agents/base.py`, `agents/cache.py` (deleted),
  `pyproject.toml`, `uv.lock` (deleted), three regenerated fixture JSON
  files, and a new `tests/test_api_client.py` (305 lines, 7 tests).

**The PR body only documents the `simulator/` half.** Its full text (`gh pr
view 27`) is "Implement CR-1, CR-2, CR-3, CR-5 (labeller, API contract,
deps, tests)" — four change requests, all about the simulator's ground-truth
labeller, its endpoint/payload fix, dependency cleanup, and boundary tests.
It explicitly "Skips CR-4 (CI/Lint) — shared infra, tracked separately with
VP." Nothing in the PR body describes the actual frontend dashboard rewrite
that the PR *title* and the bulk of the diff are about — the person merging
this had no written description of what changed on five page components, the
API client, or the type system. That is a real process gap, not a
formatting nitpick: the frontend changes are the larger and riskier half of
this diff and went in with zero narrative.

---

## 2. The six outstanding items

### a. Codegen — PARTIAL

- `frontend/package.json:11`: `"gen:api": "npx openapi-typescript
  ../backend/openapi.json -o src/types/generated.ts"` — the script exists
  now (it did not before).
- Running it produced `frontend/src/types/generated.ts` (1,867 lines,
  committed, not gitignored — `frontend/.gitignore` has no entry for it,
  `git ls-files frontend/src/types/` lists it tracked).
- **But nothing imports from it.** `grep -rln "types/generated"
  frontend/src` → zero hits. Every page, every component, and
  `lib/api-client.ts` import from `@/types/api` instead
  (`grep -rln "types/api" frontend/src` → 9 files).
- `frontend/src/types/api.ts:1-19` still carries its original header
  verbatim: `@generated — PLACEHOLDER`, "hand-aligned to
  shared/contracts.py... Once backend/openapi.json lands on main, DELETE
  this file and regenerate... Add gen:api script to package.json at that
  time." The `gen:api` script now exists exactly as that comment
  anticipated, but the file it tells you to delete was not deleted — it was
  rewritten by hand instead (359 lines, still hand-maintained, values now
  matching the real ladder — see 2d).
- No staleness check anywhere. `.github/workflows/ci.yml:79-117`'s frontend
  job runs `npm ci`, `npm run typecheck`, `npm run build` — no `gen:api`
  step, no diff-check against `generated.ts`. `backend/openapi.json` itself
  has a freshness check (`ci.yml:64-78`), but that only proves the schema
  matches the FastAPI app; it says nothing about the frontend's types.

**Verdict: the codegen pipeline was built and produces correct output, but
the app runs entirely on the hand-written file it was meant to replace.**
Two parallel type systems now exist, one live, one dead weight.

### b. Endpoint paths — NOT DONE (mostly)

Every call in `frontend/src/lib/api-client.ts`, checked against
`backend/openapi.json`'s 18 real paths:

| Call site | Path called | Exists? | Real path |
|---|---|---|---|
| `api-client.ts:71` `agentsApi.list` | `GET /agents` | ✅ | — |
| `api-client.ts:73-74` `agentsApi.get` | `GET /agents/:id` | ✅ | — |
| `api-client.ts:76-81` `agentsApi.getDecisions` | `GET /agents/:id/decisions` | ❌ 404 | no such route; decisions are listed unfiltered at `/decisions` |
| `api-client.ts:83-84` `agentsApi.getAutonomyHistory` | `GET /agents/:id/autonomy-history` | ❌ 404 | `/agents/{id}/policy-versions` |
| `api-client.ts:86-87` `agentsApi.getTrustEvaluation` | `GET /agents/:id/trust-evaluation` | ❌ 404 | `/agents/{id}/trust` |
| `api-client.ts:95-96` `recommendationsApi.list` | `GET /recommendations?status=` | ✅ | — |
| `api-client.ts:98-99` `recommendationsApi.get` | `GET /recommendations/:id` | ✅ | — |
| `api-client.ts:101-108` `recommendationsApi.resolve` | `POST /recommendations/:id/resolve` | ❌ 404 | `POST /recommendations/{id}/approve` or `/reject` — two separate endpoints, not one with a status body |
| `api-client.ts:116-132` `auditApi.list` | `GET /audit` | ❌ 404 | `/audit-log` — **identical bug to the 31-Aug baseline, byte-for-byte unfixed**, just now dead code (see below) |
| `api-client.ts:140-152` `auditLogApi.list` | `GET /audit-log` | ✅ | — |
| `api-client.ts:160-161` `auditSamplesApi.list` | `GET /audit-samples?agent_id=` | ✅ path; ⚠ param | real handler (`app/api/v1/audit.py:32-43`) takes no `agent_id` filter — the query param is silently ignored server-side |
| `api-client.ts:169-173` `simulationApi.start` | `POST /simulation/runs` | ✅ path; ❌ body | real `SimulationRunCreate` requires `phase` and `reason`, neither of which this client ever sends (confirmed live, see §6) |
| `api-client.ts:175-176` `simulationApi.listRuns` | `GET /simulation/runs` | ❌ 405 | only `POST /simulation/runs` and `GET /simulation/runs/{run_id}` exist — no list endpoint |

**Live-verified**, not just read from the schema (backend running, seeded,
Postgres) — see §6 for the exact `curl` output.

Confirmed live callers of the four still-broken paths:
`app/agents/[id]/page.tsx:91,96,101` (`getAutonomyHistory`,
`getTrustEvaluation`, `getDecisions`) and `app/approvals/page.tsx:89`
(`resolve`) — i.e. the agent detail page and the approve/reject action both
call dead endpoints today.

`auditApi` (the still-broken `/audit` client) is defined
(`api-client.ts:115-133`) but never imported or called anywhere
(`grep -rn "\bauditApi\b" frontend/src` → only its own definition) — it sits
unused, right next to the correct `auditLogApi`, as confusing dead code
rather than a live bug.

**This is not an improvement over the 31-Aug baseline in substance — it is
the same category of bug with different specific paths.** Five of thirteen
call sites hit a route that does not exist; a sixth sends a body the real
route rejects.

### c. Mock handlers — NOT DONE, in lockstep with the broken client

`frontend/src/mocks/handlers.ts:32,47,55,85,97` mock exactly the five
invented/wrong paths above (`/agents/:id/decisions`,
`/agents/:id/autonomy-history`, `/agents/:id/trust-evaluation`,
`POST /recommendations/:id/resolve`, `/audit`) — self-consistent with
`api-client.ts`, not with `backend/openapi.json`. This means MSW mode (off
by default — see §5) would make the app *look* correct while masking every
one of the real-path bugs in §2b. The mocks were kept in sync with the
broken client, not with the real backend.

### d. The autonomy model — DONE

Genuine fix, verified clean:

- `frontend/src/components/domain/AutonomyLadder.tsx:9,27-28` imports the
  real `AUTONOMY_LADDER` from `@/types/api` and iterates its five values;
  `currentRung: number // 0–4` (`AutonomyLadder.tsx:12`) — no hardcoded
  ₹3,000/15,000/50,000 anywhere in the file.
- `frontend/src/types/api.ts:54-56`: `AUTONOMY_LADDER = [500, 1000, 2500,
  5000, 10000]`, `MAX_RUNG = 4` — matches `shared/constants.py:21-23`
  exactly.
- `grep -rn "AutonomyTier\|\"low\"\|\"medium\"\|\"high\"\|3000\|15000\|50000"
  frontend/src/app/agents/page.tsx frontend/src/app/agents/[id]/page.tsx
  frontend/src/types/api.ts` → zero hits. The old `AutonomyTier` type and
  the 3-tier model are gone, not just unused.

### e. shadcn/ui — NOT DONE, unchanged from baseline

- `frontend/package.json` dependencies/devDependencies: no `shadcn`,
  `class-variance-authority`, `tailwind-merge`, `@radix-ui/*`, or any other
  shadcn-associated package.
- No `frontend/components.json` (shadcn's own config file) anywhere in the
  tree.
- `frontend/src/components/ui/` still holds exactly the same three
  hand-rolled files as before: `Icons.tsx`, `Providers.tsx`, `Sidebar.tsx` —
  none shadcn-generated.

### f. The hardcoded 0.85 threshold — PARTIAL, still live by default

`AccuracyGauge.tsx` was deleted outright (`git show --stat 8496b24`: `-80`
lines, file removed). Its job moved into
`frontend/src/components/charts/HorizontalThresholdGauge.tsx`, which was
also the file the 31-Aug baseline flagged.

- `HorizontalThresholdGauge.tsx:12,17`: `threshold?: number; // default
  0.85` / `threshold = 0.85` — the hardcoded value is still there.
- `HorizontalThresholdGauge.tsx:14,21`: a new `isHealthy?: boolean` prop was
  added with the comment "Pass from backend when available. Falls back to
  client-side derivation," and `const isHealthy = isHealthyProp ??
  wilsonLB >= threshold` — a real escape hatch was built.
- **But it is never used.** The only call site,
  `frontend/src/app/agents/[id]/page.tsx:306-309`, passes only `accuracy`
  and `wilsonLB` — no `isHealthy`. The client-side `wilsonLB >= 0.85`
  computation fires on every render, unconditionally, in practice.
- Separately: `HorizontalThresholdGauge.tsx:59` renders the literal string
  `THRESHOLD (85%)`, not `{threshPct}%` — even if a caller passed a
  different `threshold` prop, the on-screen label would still say 85%.

**Net effect: the shape now allows the backend to own this decision, but
today, live, it does not — the frontend still computes and displays its own
pass/fail verdict against a number that has no relationship to the real gate
(`MIN_TRUST_SCORE_FOR_INCREASE = 70.0` plus five other independent gates,
per the 31-Aug baseline's own finding, unchanged).**

---

## 3. New work beyond the checklist

- **The simulator fix (CR-2)**: `simulator/simulator/api_client.py` (per the
  PR body) replaces `submit_invoice()` with `submit_decision()` and switches
  from `POST /api/v1/invoices` to `POST /api/v1/decisions` with a flat body
  — this is precisely the hop-2 fix the 31-Aug audit's vertical-slice trace
  called the first break in the entire chain (`docs/audits/2026-08-31-state-audit.md`
  §6, "First break: hop 2, the simulator→backend POST"). **This is a real,
  legitimate, badly-needed fix, correctly attributed in the PR body, and not
  scope creep** — `docs/lanes/ad.md:34,37-40` has Adhya owning both
  `simulator/` and `frontend/` "through the port," so this is inside her
  actual ownership as of 2 Sept, not a boundary jump. It is filed under
  frontend's report because it rode in on a PR titled as a frontend PR, not
  because it belongs to the frontend lane.
- **2-way ground-truth labeller (CR-1)**: `simulator/simulator/labeller.py`
  changes four rules to stop emitting `ESCALATE` as ground truth. Reasonable
  on its own (ground truth is supposed to be binary — `shared/contracts.py`'s
  `DecisionRecord` docstring says ground truth is always
  `APPROVE`/`REJECT`), but it is a behavior change to existing rules with
  a stated, admitted cost: the PR body itself says "some pre-existing tests
  now fail as they assert 3-way ESCALATE behavior; fixtures need
  regeneration in a follow-up per CR scope" — a known regression, deferred,
  not hidden.
- **Dependency cleanup (CR-3)**: removes `google-generativeai` and
  `python-dotenv` from `simulator/pyproject.toml`, and fixes stale
  docstrings referencing `AgentDecisionRecord` (now `AgentOutcome`). This
  matches a specific finding from the 31-Aug audit (§4, "simulator's
  incomplete `llm.py` cleanup") — `simulator/simulator/agents/cache.py` (the
  orphaned `DecisionCache`, `-145` lines) is also deleted in this diff. Real
  cleanup of a previously-flagged item.
- **`frontend/src/types/generated.ts`**: new, 1,867 lines, entirely
  unused (§2a). This needs maintaining (re-running `gen:api` whenever
  `backend/openapi.json` changes) for zero present benefit, and nothing
  enforces that it's kept current.
- **`frontend/src/app/globals.css:203-219`**: five new `.rung-0`…`.rung-4`
  color classes backing `AutonomyLadder`'s per-rung styling — a small,
  reasonable addition in support of item 2d, not independently notable.
- **`simulator/tests/test_api_client.py`**: new, 305 lines, 7 tests,
  explicitly a boundary-contract test suite for the CR-2 fix (flat payload,
  2-way ground truth, integer amount, non-empty reason). Good practice,
  directly justified by the change it tests.

---

## 4. Boundary violations

### No business logic in TypeScript

**Two confirmed violations**, one carried over from baseline, one newly
introduced:

1. `frontend/src/components/charts/HorizontalThresholdGauge.tsx:21`:
   ```ts
   const isHealthy = isHealthyProp ?? wilsonLB >= threshold;
   ```
   with `threshold = 0.85` hardcoded at line 17. This *decides* whether an
   agent's accuracy is healthy using a number invented in the frontend, not
   the real multi-gate eligibility rule the trust engine actually applies.
   Unchanged in substance from the 31-Aug baseline finding (§2f above).

2. **New**: `frontend/src/app/audit/page.tsx:31-45`:
   ```ts
   function verifyChain(entries: AuditLogEntry[]): {
     valid: boolean; checkedCount: number; brokenAt: number | null;
   } {
     if (entries.length === 0) return { valid: true, checkedCount: 0, brokenAt: null };
     for (let i = 1; i < entries.length; i++) {
       if (entries[i].prev_hash !== entries[i - 1].hash) {
         return { valid: false, checkedCount: i, brokenAt: i };
       }
     }
     return { valid: true, checkedCount: entries.length, brokenAt: null };
   }
   ```
   This *recomputes* hash-chain integrity client-side and drives the
   "Hash Chain: Verified" badge (`audit/page.tsx:79-102`) from it. It is
   strictly weaker than the real check — it only compares `prev_hash`/`hash`
   string equality between adjacent rows *on the currently loaded page*
   (25 entries), never recomputing `sha256(prev_hash + canonical_json(payload))`
   the way `backend/app/models/audit_hash.py:29-31` and the live
   `verify_chain()` behind `GET /audit-log` (`backend/app/api/v1/audit.py`,
   landed in PR #26, already on `main`) do. **The backend now returns
   `chain_valid`/`chain_verified_scope` computed from the full table
   (confirmed live in §6) — the frontend ignores both fields entirely.**
   `grep -rn "chain_valid" frontend/src` → zero hits; the type this endpoint
   is fetched into, `PaginatedResponse<AuditLogEntry>`
   (`api-client.ts:143`, `types/api.ts:354`), has no such field at all. This
   is exactly the "two sources of truth" failure mode `docs/lanes/ad.md:92-96`
   names by name, in the one place — an immutable audit trail — where it
   matters most.

**False positives explicitly cleared**: `samplingRateOf`/`rungOf`/`limitOf`
(`frontend/src/types/api.ts:66-84`, called at e.g.
`app/agents/[id]/page.tsx:122,385`) are pure lookups into the same fixed
five-element array the ladder itself is rendered from — they decide nothing
from live evidence, the same class of derivation as rendering
`AUTONOMY_LADDER[rung]` for a label. `trust_score`, `drift_severity`,
`eligible_for_increase`, `wilson_lower`/`wilson_upper` are read as-is from
API payloads everywhere else checked
(`app/agents/page.tsx:34,102-104,135`, `app/agents/[id]/page.tsx:144-146,167,188,203-204,272-273`)
— rendered, not computed.

### No hand-edited generated types

Cannot be fully proven without independently regenerating and diffing, but
no evidence of tampering: `types/generated.ts` reads as raw
`openapi-typescript` output (consistent header comment style, no
inline `// TODO` or narrative comments of the kind every other file in this
codebase carries). Moot in practice — it's unused (§2a).

### No direct database access, no importing Python

Clean. `grep -rniE "psycopg|sqlalchemy|import .*\bbackend\b|from .*backend"
frontend/src` → zero hits.

### Nothing written outside `frontend/`

**Real finding, not a false positive, verdict: legitimate, not a
violation.** `simulator/` is touched (§1, §3) — 11 files, +2,949/−4,401. Per
`docs/lanes/ad.md:27-40`, Adhya owns `simulator/` "through the port," with
handoff to Utkarsh scheduled for `docs/DEADLINES.md`'s Fri 4 Sept
deliverable — after this PR's 2 Sept merge date. The change fixes a
previously-flagged, blocking bug (§3, CR-2) and is honestly described in the
PR body as simulator work, just bundled into a PR whose title only names
`frontend/`. The boundary crossed is the PR's own title, not the actual
ownership map — a documentation/framing issue (§1), not an unauthorized
lane incursion.

---

## 5. Does it actually run

All commands run from `frontend/`, fresh `npm install`:

```
$ npm install
added 21 packages, and audited 473 packages in 3s
161 packages are looking for funding
found 0 vulnerabilities
```

```
$ npm run typecheck
> aag-frontend@0.1.0 typecheck
> tsc --noEmit
(clean exit, no output)
```

```
$ npm run build
> aag-frontend@0.1.0 build
> next build

▲ Next.js 16.3.2 (Turbopack)
✓ Compiled successfully in 12.9s
  Running TypeScript ...
  Finished TypeScript in 4.3s ...
✓ Generating static pages using 9 workers (7/7) in 1267ms

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /agents
├ ƒ /agents/[id]
├ ○ /approvals
├ ○ /audit
└ ○ /simulation
```

Both clean. `npm run lint`:

```
$ npm run lint
> aag-frontend@0.1.0 lint
> eslint

Oops! Something went wrong! :(
ESLint: 9.39.5
ESLint couldn't find an eslint.config.(js|mjs|cjs) file.
```

**Fails outright — no ESLint v9 flat config exists anywhere in `frontend/`.**
Matches the PR's own admission ("Skips CR-4 (CI/Lint)"). Not run in CI
either — `.github/workflows/ci.yml:79-117`'s frontend job runs `npm ci`,
typecheck, build; no lint step.

**MSW is still disabled by default**, unchanged from baseline:
`frontend/src/components/ui/Providers.tsx:38,42`: gated on
`process.env.NEXT_PUBLIC_MSW_ENABLED !== "true"`; no `.env` file in the repo
sets it. A plain `npm run dev` hits the real API base URL
(`NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000` —
`api-client.ts:23-24`) directly.

With MSW off and no backend running: only `app/agents/page.tsx:27,81-85`
handles this explicitly (`isError` → "Unable to connect to governance API.",
in red). Every other page silently swallows the failure:
`app/agents/[id]/page.tsx:89,94,99` destructure `history = []` /
`trustEval` / `decisions` with no `isError` check at all;
`app/approvals/page.tsx:82` defaults `recommendations = []`;
`app/audit/page.tsx:52` leaves `data` `undefined` and the page renders "No
entries to verify"; `app/simulation/page.tsx:17` defaults `runs = []`.
`grep -rn "isError" frontend/src/app` → one hit, `agents/page.tsx:27,81`.
**Four of five pages present a clean-looking empty state indistinguishable
from "genuinely nothing here yet" when the real cause is "couldn't reach the
backend at all."** No React error boundary exists anywhere
(`find frontend/src -iname "error.tsx"` → zero results), so any page that
*did* throw would show Next's default unstyled dev overlay (or a blank
white screen in production), not a designed fallback.

---

## 6. Against the real backend

Fresh Postgres (`docker compose down -v db && docker compose up -d --wait
db`), `alembic upgrade head`, `python -m backend.app.seed`, `uvicorn
app.main:app --port 8000` — all clean. Frontend run with
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, MSW off (default),
`npm run dev --port 3000`. CORS confirmed permissive for this origin
(`backend/app/main.py:34-38`: `allow_origins=["http://localhost:3000"]`).

Every call the frontend actually makes, replicated with `curl` against the
live, seeded backend:

```
GET /agents                                  → 200, 3 real agents
GET /agents/agent-01                         → 200, real AgentOut
GET /agents/agent-01/autonomy-history        → 404 {"detail":"Not Found"}
GET /agents/agent-01/trust-evaluation        → 404 {"detail":"Not Found"}
GET /agents/agent-01/decisions                → 404 {"detail":"Not Found"}
GET /recommendations?status=PENDING          → 200, real, rich data
POST /recommendations/rec-agent01-001/resolve → 404 {"detail":"Not Found"}
GET /audit-log?page=1&page_size=25           → 200, chain_valid: true
GET /simulation/runs                         → 405 Method Not Allowed
POST /simulation/runs (frontend's exact body) → 422, missing "phase" and "reason"
```

Per route:

- **`/agents`** — renders real data. `agentsApi.list` hits the one real,
  correctly-shaped call this page makes. **But**: the real `AgentOut`
  payload (`{id, name, current_limit, current_rung, state, context}`,
  confirmed via live `GET /agents` response body) has **no** `trust_score`,
  `drift_severity`, `wilson_lower`, `wilson_upper`, `eligible_for_increase`,
  or `rolling_accuracy` field — fields `AgentSummary`
  (`frontend/src/types/api.ts`) declares and `app/agents/page.tsx:34,102-104,135`
  reads unconditionally. `agents/page.tsx:135`:
  `{agent.trust_score.toFixed(1)}` calls `.toFixed()` on `undefined`; line
  `103`: `agent.drift_severity.toLowerCase()` is reached because
  `agent.drift_severity !== "NONE"` evaluates `undefined !== "NONE"` →
  `true`, then crashes calling `.toLowerCase()` on `undefined`. **This is
  inferred from source plus the confirmed live response shape, not observed
  in a rendered browser** (no browser-automation tool was available in this
  audit) — but the reasoning is direct: the field genuinely does not exist
  on the wire, the code genuinely calls a method on it with no guard, and
  no error boundary exists to catch it. On the evidence available, the
  first screen a demo would show is expected to throw.
- **`/agents/{id}`** — same root cause as above, worse coverage: `agent`
  itself (from the one working call) is missing the same fields, so
  `app/agents/[id]/page.tsx:188` (`agent.trust_score.toFixed(1)`) hits the
  identical crash. Of its four data fetches, three 404
  (`getAutonomyHistory`, `getTrustEvaluation`, `getDecisions`) and are
  silently swallowed to empty defaults (§5) — so even past the crash, the
  ladder position, trust-over-time, Wilson band, drift indicator, and
  decision history would all render as empty.
- **`/approvals`** — the **list half genuinely works**: `GET
  /recommendations?status=PENDING` returns real `Recommendation` rows with
  full `opinions[]` (agent_name/verdict/reasoning/concerns/confidence),
  `has_dissent`, `clamped`/`clamped_from`, `rationale` — everything
  `app/approvals/page.tsx` and its `OpinionCard` (lines 49-74) render. The
  **write half is fully broken**: pressing Approve/Reject calls
  `recommendationsApi.resolve` → `POST
  /recommendations/{id}/resolve` → live 404. The human-authorization
  action — the one ad.md (line 138-142) calls the point of this whole
  screen — does not work against the real API today.
- **`/audit`** — renders real data, correctly. `auditLogApi.list` hits the
  right path. One live-verified cosmetic mismatch: real `event_type` values
  are dotted (`"decision.recorded"`, `"policy_version.created"`,
  `"recommendation.approved"`, `"audit_sample.reviewed"`), but
  `EVENT_TYPE_BADGE` (`app/audit/page.tsx:17-25`) keys on underscored names
  that don't exist in the real system at all (`agent_registered`,
  `autonomy_changed`, `drift_detected`, `recommendation_created`) — every
  row falls through to the generic gray badge; `fmtEventType`
  (`audit/page.tsx:27-29`) doesn't split on `.`, so a row displays
  "Decision.recorded" rather than "Decision Recorded." The chain-integrity
  badge itself (§4) shows a correct "Verified" today only because the seeded
  data happens to be genuinely unbroken — it would show the same badge even
  if only the *displayed page* were tampered with elsewhere in a longer
  chain, since it never checks past what's loaded.
- **`/simulation`** — list panel silently renders empty (`GET
  /simulation/runs` 405, swallowed to `runs = []`, §5). Start Simulation is
  broken by request-body shape, live-confirmed: the frontend posts
  `{invoice_count, seed, agent_type, agent_id, api_base_url}`
  (`app/simulation/page.tsx:24-30`); the real `SimulationRunCreate` schema
  requires `phase` and `reason` (neither sent) and doesn't accept
  `agent_type`/`api_base_url` at all — live `curl` with the frontend's exact
  body returns `422`, `"missing": ["body","phase"]` and
  `["body","reason"]`.

**Summary: 1 of 5 routes (audit) works end to end against the real backend.
1 of 5 (agents list) is expected to crash on render due to a payload-shape
mismatch. 1 of 5 (agent detail) both crashes and has 3 of 4 data calls
404ing. 1 of 5 (approvals) reads real data but cannot write. 1 of 5
(simulation) is silently empty and its one action 422s.**

---

## 7. The demo beats

| Beat | Can the UI show it today? | Evidence |
|---|---|---|
| Five-rung ladder, agent's current position | **Component: yes. Wired: yes.** `AutonomyLadder.tsx` (§2d) takes real `AUTONOMY_LADDER` + `currentRung`; called from `app/agents/[id]/page.tsx` off `agent.current_rung`, which the real `/agents/{id}` payload does provide. Blocked only by the render crash in §6 happening earlier in the same page. |
| Accuracy with a narrowing Wilson band | **No, not wired.** `AutonomyTimeline.tsx:57-60` plots `wilsonLower`/`wilsonUpper` correctly from `AutonomyEvent[]` — but that array comes from `agentsApi.getAutonomyHistory`, which 404s live (§6). The chart is real; its data source is not. |
| Drift status, recent vs. baseline | **Field exists, not populated.** `agent.drift_severity` is read in three places (§4 false-positive list) but the real `/agents`/`/agents/{id}` payload never includes it (§6) — always `undefined` on screen. |
| Four governance opinions, dissent surfaced | **Yes, works today.** `app/approvals/page.tsx:49-74,176-185,229-244` renders `opinions[]`, `has_dissent`, per-opinion `verdict`/`reasoning`/`concerns`/`confidence` from the real, live `GET /recommendations` response (§6) — confirmed with real seed data. |
| The clamp — `clamped`/`clamped_from` | **Yes, works today.** `approvals/page.tsx:176-180` — same live-confirmed call as above; the seeded `rec-agent01-001` is `clamped: true, clamped_from: 10000` and would render as "CLAMPED from ₹10k." |
| Audit chain verification (`chain_valid`) | **Partially, and dishonestly.** A badge is shown (`audit/page.tsx:79-102`), but it is driven by a weaker client-side recomputation (§4) that ignores the real `chain_valid`/`chain_verified_scope` the API now returns (confirmed live in §6). It would currently show the *right answer* on seeded data by coincidence, not because it reads the real field. |
| Autonomy over time, an increase and a clawback | **No.** Same root cause as the Wilson band: `AutonomyTimeline.tsx` is a real, capable component (promotion/clawback event markers exist in its code), fed exclusively by `getAutonomyHistory`, which 404s live. |

---

## 8. What's left

1. Fix `agentsApi.getAutonomyHistory` (`frontend/src/lib/api-client.ts:83-84`) to call
   `GET /agents/{id}/policy-versions` instead of the nonexistent
   `/agents/{id}/autonomy-history`, and reshape the response mapping —
   `policy-versions` returns `PolicyVersionOut[]` (`id, agent_id, limit,
   rung, effective_from, created_by, reason, previous_version_id`), not the
   invented `AutonomyEvent` shape the frontend currently expects.
2. Fix `agentsApi.getTrustEvaluation` (`api-client.ts:86-87`) to call
   `GET /agents/{id}/trust` instead of `/agents/{id}/trust-evaluation`.
3. Remove `agentsApi.getDecisions` (`api-client.ts:76-81`) — there is no
   per-agent decisions route. Either filter `GET /decisions` client-side by
   `agent_id`, or ask the backend lane to add the filter server-side.
4. Fix `recommendationsApi.resolve` (`api-client.ts:101-108`) — split into
   two calls, `POST /recommendations/{id}/approve` and
   `POST /recommendations/{id}/reject`, matching the real two-endpoint
   shape; update `app/approvals/page.tsx:87-99`'s mutation accordingly. This
   is the single highest-value fix — it's the actual human-approval action.
5. Delete the dead `auditApi` object (`api-client.ts:115-133`) — unused,
   hits a path that doesn't exist, confusing next to the correct
   `auditLogApi`.
6. Fix `simulationApi.listRuns` (`api-client.ts:175-176`) — no such GET
   endpoint exists; either drop the "runs list" panel or ask backend to add
   one.
7. Fix `simulationApi.start`'s request body (`api-client.ts:169-173`,
   called from `app/simulation/page.tsx:24-30`) to send `phase` and
   `reason` (both required, currently absent) and drop `agent_type`/
   `api_base_url` (not part of the real schema).
8. Fix or drop every field on `AgentSummary`
   (`frontend/src/types/api.ts`, consumed at
   `app/agents/page.tsx:34,102-104,135` and
   `app/agents/[id]/page.tsx:167,188,203-204,272-273,305-309`) that the real
   `AgentOut` schema doesn't provide (`trust_score`, `drift_severity`,
   `wilson_lower`, `wilson_upper`, `eligible_for_increase`,
   `rolling_accuracy`) — these have to come from a join with
   `GET /agents/{id}/trust` (item 2), not from the agent object itself. This
   is the fix for the render crash in §6 and is more urgent than the
   cosmetic items above it.
9. Wire `audit/page.tsx` to the real `chain_valid`/`chain_verified_scope`
   fields (already returned by `GET /audit-log`, per PR #26) instead of the
   client-side `verifyChain()` re-implementation at
   `app/audit/page.tsx:31-45` — delete that function, add
   `chain_valid`/`chain_verified_scope` to the response type, render those
   fields directly.
10. Wire `HorizontalThresholdGauge`'s `isHealthy` prop
    (`app/agents/[id]/page.tsx:306-309`) from whatever real signal the
    backend can provide instead of leaving it unset — or accept the
    threshold display is decorative and stop implying it's a real gate.
11. Add an ESLint v9 flat config (`frontend/eslint.config.js`) so
    `npm run lint` (currently hard-failing) actually runs, and add a lint
    step to `.github/workflows/ci.yml`'s frontend job.
12. Either delete `frontend/src/types/generated.ts` or actually cut the app
    over to it — right now it's 1,867 committed, unused, unmaintained lines.
13. Add `isError` handling (matching `app/agents/page.tsx:81-85`'s pattern)
    to `agents/[id]/page.tsx`, `approvals/page.tsx`, `audit/page.tsx`, and
    `simulation/page.tsx` — right now a real backend outage and "nothing to
    show yet" render identically.
14. shadcn/ui is still entirely absent (`docs/lanes/ad.md:256-258` names it
    as part of the fixed stack) — install it and add `components.json`, or
    get an explicit decision that it's cut from scope.
15. Regenerate `simulator/tests/`' pre-existing fixtures that the PR's own
    body admits now fail against the 2-way labeller change (CR-1) — a
    stated, deferred follow-up, not new information.

---

## 9. Verdict

If the demo were tomorrow: the landing agents list would very likely crash
on load (a payload-shape mismatch between the real `AgentOut` and what the
page unconditionally reads), with no error boundary to catch it — the first
screen a judge sees is the least reliable one in the app. If that were
patched around live, the approvals queue would show real, richly-rendered
governance opinions, dissent, and the clamp — genuinely good, working
UI — right up until someone actually clicked Approve or Reject, which 404s.
The audit trail would render correctly and show a "Verified" badge, but for
the wrong reason — it never reads the real `chain_valid` the backend now
computes. The agent detail page — ad.md's "most important screen in the
product," carrying the ladder, the Wilson band, drift status, and autonomy
history — would show the ladder skeleton and then largely nothing else,
because three of its four data calls hit routes that don't exist. The
simulation console would look empty and its one button would fail
validation. The five-rung ladder, the governance-opinions panel, and the
clamp display are real, finished work. The Wilson band, drift-over-time,
autonomy history, and the actual approve/reject action — the parts of the
ten-beat arc that show the system *changing* — are not connected to
anything real today.
