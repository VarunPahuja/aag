# Port Feasibility — `origin/ad/simulator-frontend` vs. `main`'s frozen `shared/`

Read-only. No branch created, nothing edited, no port attempted. This
compares `origin/ad/simulator-frontend` (`1b1c416`, Adhya Sharma,
2026-08-23) against `origin/main`'s frozen v1.1 `shared/` (`7922bc0`). See
`docs/audits/2026-08-23-state-audit.md` §2/§3/§9 for how this divergence
happened and why it matters — this report only answers "what does fixing it
cost."

Scope, per the brief: every file in `simulator/` and `frontend/src/` on the
branch. `frontend/nexttemp/` (the leftover scaffold, see state-audit §4) and
config/lockfiles outside `frontend/src/` are out of scope for the file table
but noted where relevant.

## Classification key

- **RENAME** — only type/enum/constant names change; logic untouched.
- **REWRITE** — logic depends on the 3-tier model, invented backend
  endpoints, or a concept `main`'s `shared/` defines differently.
- **LOCAL** — depends on nothing in `shared/`, or only on concepts that are
  legitimately simulator-local and can keep their own types.
- **DISCARD** — leftover scaffold, duplicated logic, or superseded by `main`.

---

## File-by-file: `simulator/`

| File | Class | Lines | Reason |
|---|---|---:|---|
| `simulator/pyproject.toml` | RENAME | 29 | Package config; deps (`pydantic`, `google-generativeai`, `httpx`, `typer`, `rich`) are all still needed post-port, only the package name/description reference the old framing |
| `simulator/uv.lock` | DISCARD | 1,037 | Lockfile, regenerates automatically from `pyproject.toml` — nothing to port |
| `simulator/simulator/__init__.py` | LOCAL | 1 | Empty package marker |
| `simulator/simulator/__main__.py` | RENAME | 4 | Just imports `cli.app` |
| `simulator/simulator/agents/__init__.py` | LOCAL | 1 | Empty package marker |
| `simulator/simulator/agents/base.py` | RENAME | 56 | `AgentProtocol` only references `Invoice`/`AgentDecisionRecord` by name in type hints — structurally a `Protocol`, no tier logic anywhere |
| `simulator/simulator/agents/cache.py` | RENAME | 145 | Content-hash file cache keyed on invoice fields (`vendor_name`, `amount`, `category`, ...) + prompt version — none of the hashed fields are tier/limit concepts |
| `simulator/simulator/agents/llm.py` | **REWRITE** | 242 | `SYSTEM_PROMPT` (lines ~62-84) hardcodes the exact 3-tier/category limit table as natural-language instructions to Gemini ("travel: ₹3,000 \| consulting: ₹4,000 \| software: ₹5,000...") and reasons about "a higher-tier approver." Rewriting means rewriting the prompt's policy-rules section and the tier-vs-rung framing, not just renaming a type |
| `simulator/simulator/agents/scripted.py` | **REWRITE** | 146 | `_rule_based_decision`, `_get_limit`, `_get_high_limit` (lines 100-146) look up `CATEGORY_LIMIT_OVERRIDES[tier][category]` directly — the entire decision boundary is defined in terms of the tier table |
| `simulator/simulator/api_client.py` | **REWRITE** | 154 | Every domain endpoint method (`submit_invoice` → `POST /invoices`, etc.) targets a URL/payload shape with no counterpart in the real API (see Q5). The `_request`/retry/auth wrapper (lines 120-154) is generic and survives |
| `simulator/simulator/cli.py` | RENAME | 318 | Typer command wiring; only touches tier concepts via the types it imports and via `runner.wilson_lower_bound` (needs repointing to `trust`'s version once that's deleted from `runner.py`, see Q3) |
| `simulator/simulator/distributions.py` | LOCAL | 167 | `DistributionParams` and the three phase presets (`baseline_params`/`shifted_params`/`recovery_params`) are pure difficulty-tuning knobs (log-normal mu/sigma, missing-field probability, ambiguous-vendor probability) — none of this is a `shared/` concept even on her own branch; it's simulator-local config that happens to sit in her `shared/constants.py` by choice, not necessity |
| `simulator/simulator/generator.py` | **REWRITE** | 317 | Mostly LOCAL (vendor/employee/department/date pools, log-normal amount draw) — but `_pick_amount` and `_is_boundary_amount` (lines ~222-260) target the boundary zone using `CATEGORY_LIMIT_OVERRIDES["low"]`, and this boundary-case generation is the mechanism that makes the degraded phase "genuinely hard" (the file's own stated design goal). That coupling makes the file REWRITE overall even though most of its lines don't touch the tier table directly |
| `simulator/simulator/labeller.py` | **REWRITE** | 144 | The 10-rule priority order (module docstring, lines 12-21) has 3 of its 10 rules (`exceeds HIGH tier limit`, `exceeds current tier limit`, `boundary zone`) defined directly against `TIER_LIMITS`/`CATEGORY_LIMIT_OVERRIDES` — this is the oracle; every downstream accuracy number depends on it. See Q1 for the full quote |
| `simulator/simulator/runner.py` | **REWRITE** | 176 | Orchestration itself (lines 66-176) is RENAME-grade — but it defines its own `wilson_lower_bound()` (lines 56-63), which per ADR-0010's stated intent is deleted in favour of importing `trust/trust_engine/stats/wilson.py`'s version. Small diff, but it's a rewrite of a duplicated statistical function, not a rename |
| `simulator/tests/__init__.py` | LOCAL | 2 | Empty |
| `simulator/tests/conftest.py` | RENAME | 15 | Fixture wiring only |
| `simulator/tests/test_error_rate_validation.py` | **REWRITE** | 242 | Validates the "good phase ~5-15% error, degraded phase >20%" claim by running `ScriptedAgent` + `GroundTruthLabeller` — both REWRITE, so the concrete assertions break, though the *validation concept* (loose, relative-ordering thresholds, its own docstring says so) is worth re-running against the ported version |
| `simulator/tests/test_generator.py` | RENAME | 261 | 24 tests, **zero** hits for tier/limit vocabulary in a targeted grep — seeding, vendor-pool, date-range, and reproducibility tests, none of which touch `_pick_amount`'s boundary-case branch specifically. Caveat: this file tests `generator.py`, which is itself REWRITE for a different subset of its behaviour — these particular 24 tests should survive a rename-only port, but don't currently exercise the part of `generator.py` that will actually change |
| `simulator/tests/test_labeller.py` | **REWRITE** | 305 | 25 tests, 4 tier/limit references — directly asserts the rule-priority-order outcomes (rules 6-8) that depend on `TIER_LIMITS`/`CATEGORY_LIMIT_OVERRIDES` |
| `simulator/tests/test_runner.py` | **REWRITE** | 222 | 19 tests, 19 tier/wilson references — essentially the whole file exercises `wilson_lower_bound()` and tier-shaped `SimulationRunResult` fields |
| `simulator/tests/test_scripted_agent.py` | **REWRITE** | 174 | 13 tests; literal tier/limit constants don't appear in the test file itself, but every test calls `ScriptedAgent.decide()` (REWRITE) and several assert on specific `reason` codes tied to the tier rule set — the *properties* tested (determinism, confidence-on-error, seed-reproducibility) are exactly what should be re-asserted post-port, but the assertions themselves will need new expected values |
| `simulator/fixtures/good.json` | DISCARD | 4,206 | Generated data, keyed to the wrong ground-truth rules — regenerate via `simulator generate` once `labeller.py`/`generator.py` are ported, don't port the data itself |
| `simulator/fixtures/degraded.json` | DISCARD | 4,308 | Same reason |
| `simulator/fixtures/recovery.json` | DISCARD | 4,229 | Same reason |
| `simulator/fixtures/.gitkeep` | DISCARD | 0 | Redundant next to the 3 real fixture files (already flagged in the 23 Aug state audit) |
| `simulator/fixtures/cache/.gitkeep` | LOCAL | 4 | Legitimate placeholder for the (empty) LLM-response cache dir, keeps regardless |

**`simulator/` subtotal:** RENAME 828, REWRITE 2,120, LOCAL 175, DISCARD 13,780 (line count; see full totals below — the 4 fixture files alone are 92% of the DISCARD bucket and 62% of everything in `simulator/`).

---

## File-by-file: `frontend/src/`

| File | Class | Lines | Reason |
|---|---|---:|---|
| `app/page.tsx` | LOCAL | 2 | `redirect("/agents")`, nothing else |
| `app/layout.tsx` | LOCAL | 44 | Font + `Providers`/`Sidebar` wrapper, no domain types |
| `app/globals.css` | LOCAL | 195 | Pure CSS, survives regardless of any port decision |
| `app/agents/page.tsx` | **REWRITE** | 164 | 8 hits for tier/`AutonomyTier` — the agents-list view renders tier badges and tier-scoped limits directly |
| `app/agents/[id]/page.tsx` | **REWRITE** | 286 | 8 hits — the agent detail hero page, same coupling, plus it's the page that should host the real 5-rung ladder and Wilson band per `docs/lanes/ad.md` |
| `app/approvals/page.tsx` | **REWRITE** | 163 | 0 tier hits directly, but built entirely on `approvalsApi`/`HumanApproval` (both REWRITE) — no `AgentOpinion`/dissent rendering exists at all, which is a missing feature, not just a rename |
| `app/audit/page.tsx` | **REWRITE** | 210 | Consumes `AgentDecisionRecord`/`AgentDecision` (REWRITE'd types) and `auditApi`; page structure (table + detail drawer) is reusable, the data layer under it is not |
| `app/simulation/page.tsx` | **REWRITE** | 222 | Consumes `SimulationRunConfig`/`SimulationRunResult` and `simulationApi` — the one API family that's structurally closest to real (`/simulation/runs` matches `vp/backend`'s planned endpoint almost exactly), but the config/result field names still need a full type swap |
| `components/charts/AccuracyGauge.tsx` | **REWRITE** | 80 | Takes `wilsonLB` as a prop (good — no self-computed stats) but hardcodes `threshold = 0.85` and computes `isHealthy` client-side, both tied to her single-threshold eligibility model, not the real 6-condition gate |
| `components/charts/AutonomyTimeline.tsx` | RENAME | 241 | Best-preserved file in the branch — a generic Recharts `ComposedChart` (Area+Line+ReferenceLine) driven entirely by `AutonomyEvent`-shaped data (`limit_amount`, `rolling_accuracy`, `wilson_lower_bound`, `is_clawback_event`, `is_promotion_event`, `drift_direction`). None of the chart mechanics assume a 3-tier scale — feed it real `TrustEvaluation`-derived events with `current_limit` in `AUTONOMY_LADDER` units and `direction: Direction` instead, and it plots the real ladder correctly. This is close to exactly the "single most valuable visualisation" `docs/lanes/ad.md` asks for |
| `components/charts/HorizontalThresholdGauge.tsx` | **REWRITE** | 81 | `threshold = 0.85` matches her `CLAWBACK_THRESHOLD` exactly; `isHealthy = wilsonLB >= threshold` is a single-number gate. The real system's eligibility is `trust_score >= 70.0` (a 4-component weighted composite) plus 5 other independent gates (sample size, cooldown, drift, max rung, clawback recovery) — not representable as one threshold line, needs a different visual metaphor entirely, not a relabelling of this one |
| `components/domain/ApprovalRow.tsx` | **REWRITE** | 99 | `HumanApproval` (approval_id/status/resolved_by/resolution_note) has no `rationale`, no `proposed_limit`/`proposed_rung`, and no per-agent `opinions` — `Recommendation`'s richer shape (and the disagreement surfacing `docs/lanes/ad.md` calls "the most useful thing on the screen") isn't representable by a rename; the optimistic-update/loading-state UX pattern is reusable, the data model isn't |
| `components/domain/AutonomyLadder.tsx` | **REWRITE** | 46 | Hardcodes 3 tiers at ₹3,000/₹15,000/₹50,000 directly in the component (not even read from her own `shared/constants.py`) — needs rebuilding around the real 5 rungs, not a relabel |
| `components/domain/InvoiceCard.tsx` | RENAME | 73 | Only 1 hit, and it's a label string (`escalate_exceeds_tier: "Exceeds tier"`) inside a reason-code-to-label map — swap the map's keys for the real reason codes and the component logic is untouched |
| `components/ui/Icons.tsx` | LOCAL | 95 | Pure inline SVGs, zero domain types |
| `components/ui/Providers.tsx` | LOCAL | 53 | TanStack Query + MSW bootstrap, generic |
| `components/ui/Sidebar.tsx` | LOCAL | 78 | Nav shell, route labels only |
| `lib/api-client.ts` | **REWRITE** | 165 | `apiFetch` wrapper (JWT header, base URL, error handling — lines 1-71) is generic and reusable; every one of the 5 exported API objects (`agentsApi`, `approvalsApi`, `auditApi`, `invoicesApi`, `simulationApi`) targets endpoint paths and payload shapes with no match in `vp/backend`'s planned surface except `simulationApi` (see Q5) |
| `lib/query-client.ts` | LOCAL | 33 | Generic TanStack `QueryClient` config (2s polling), no domain types |
| `mocks/browser.ts` | LOCAL | 11 | MSW worker bootstrap, generic |
| `mocks/data.ts` | **REWRITE** | 169 | 25 tier hits — seed data is hand-built around 3 agents at specific tiers with tier-shaped limits; needs full regeneration against the 5-rung ladder |
| `mocks/handlers.ts` | **REWRITE** | 117 | Mirrors `api-client.ts`'s endpoint list — same fate, rewrite in lockstep with it |
| `types/api.ts` | **REWRITE** | 176 | Its own header says "mirroring shared/contracts.py Pydantic models" — full type rewrite against the real `shared/contracts.py`, no shortcut available |

**`frontend/src/` subtotal:** RENAME 314, REWRITE 1,980, LOCAL 511, DISCARD 0.

*(Not in the requested scope, but relevant: `frontend/nexttemp/` — ~7,000 lines, entirely DISCARD, default `create-next-app` scaffold that currently breaks `tsc --noEmit` — see state-audit §4/§7.)*

---

## The seven questions

### 1. `labeller.py` — how is ground truth determined?

Pure rule-based, 10 rules in strict priority order (`simulator/simulator/labeller.py:12-21`, logic at `:75-131`). Quoted directly from the module docstring:

```
RULE PRIORITY ORDER:
  1. Missing required fields               → ESCALATE (escalate_missing_fields)
  2. Blocked vendor                        → REJECT   (reject_blocked_vendor)
  3. Invalid category                      → REJECT   (reject_invalid_category)
  4. Negative / zero amount                → REJECT   (reject_negative_amount)
  5. Future invoice date                   → REJECT   (reject_future_date)
  6. Amount exceeds HIGH tier limit        → REJECT   (reject_exceeds_limit)
  7. Amount exceeds current tier limit     → ESCALATE (escalate_exceeds_tier)
  8. Amount in boundary zone (±5 %)       → ESCALATE (escalate_boundary_amount)
  9. Ambiguous vendor + non-trivial amount → ESCALATE (escalate_ambiguous_vendor)
 10. Everything else                       → APPROVE  (approve_within_limit)
```

Rules 6-8 (`:118-133` in the code) call `self._get_limit(cat, tier)`, which is a direct `CATEGORY_LIMIT_OVERRIDES[tier][category]` lookup with `TIER_LIMITS[tier]` as fallback (`:139-144`). **Yes, it depends directly on `TIER_LIMITS`/`CATEGORY_LIMIT_OVERRIDES`.**

**Can the same approach be expressed against the 5-rung `AUTONOMY_LADDER`, or is the concept itself different?** The *approach* — a priority-ordered rule cascade ending in a limit comparison — ports cleanly. The *specific rules* don't, because the model has one fewer dimension: her limits are a 2D table (tier × category, 15 cells), the real ladder is a 1D scale (5 rungs, no category distinction at all — `shared/constants.py` has no concept of invoice category affecting the limit). Porting rules 6-8 means collapsing "exceeds HIGH-tier limit for this category" into "exceeds the top rung (₹10,000)" and "exceeds current-tier limit for this category" into "exceeds the agent's current rung," which is a straightforward simplification, not a re-design — but it does mean category stops mattering to the labeller at all, which changes what "boundary case" (rule 8) means: instead of ±5% of a category-specific number, it becomes ±5% of whichever flat rung amount the agent currently sits at. **The labelling *concept* (deterministic rule cascade, ground truth independent of any agent) survives; the specific rule bodies need rewriting, and one entire axis of difficulty (category-based tiering) disappears unless the team decides to reintroduce it as a genuinely new `shared/` concept** (see §6 note below on `CATEGORY_LIMIT_OVERRIDES` as a "future work" idea).

### 2. `agents/scripted.py` — same question, for whether the agent may act autonomously

It doesn't decide "may I act autonomously" at all — it decides the invoice's outcome using its own smaller rule set (`_rule_based_decision`, `scripted.py:100-116`): missing fields → ESCALATE, amount ≤ 0 → REJECT, invalid category → REJECT, amount > `_get_high_limit` → REJECT, amount > `_get_limit` → ESCALATE, else APPROVE. `_get_limit`/`_get_high_limit` (`:139-146`) are the same `CATEGORY_LIMIT_OVERRIDES` lookups as the labeller, just with a smaller rule set (no boundary-zone or ambiguous-vendor escalation) and a `random.Random`-seeded error-injection layer (`decide`, `:70-88`) that flips a fraction of otherwise-correct decisions.

**This surfaces a second, independent architecture concern beyond the tier-vs-rung mismatch**: the agent is checking its own limit and self-restricting its decision (REJECT/ESCALATE past a threshold) *inside the simulator*. Per ADR-0003, this is explicitly not where that check is supposed to live — "a deterministic Policy Engine... not by prompting the agent to respect its own limit," with the Policy Engine owned by `backend/app/policy/`. In the real architecture, the simulator's agent should be free to decide APPROVE and have the *backend* reject/escalate it if it's over the agent's actual limit; here, the agent enforces the limit on itself before the decision even leaves the simulator. This isn't blocking for a port (the demo can still work with the agent self-limiting), but it's worth a team decision on whether to fix it during the port or note it as a known simplification.

### 3. `runner.py` — what does it compute beyond orchestration, and does it duplicate/contradict `trust/trust_engine/`?

Beyond looping over invoices and calling `agent.decide()`: it tracks running counts (`approved_count`/`rejected_count`/`escalated_count`/`correct_decisions`, `runner.py:161-172`) and, at the end of a run, computes two numbers over the **entire batch**: `accuracy = correct_decisions / total_invoices` and `wilson_lower_bound(correct_decisions, total_invoices)` using its own reimplementation of the Wilson formula (`:56-63`, quoted in the state audit's §2).

**It does not do drift detection.** No recent-vs-baseline split, no two-proportion z-test, no critical-error weighting, no `DriftResult`-shaped output anywhere in the file — `grep -n "drift\|baseline\|z_stat" simulator/simulator/runner.py` → 0 hits. So the duplication is narrower than "reimplements the trust engine": it duplicates exactly one function, `wilson_lower_bound`, computed over a flat whole-run window rather than `trust/trust_engine/stats/drift.py`'s recent-50-vs-baseline split. It doesn't contradict `trust/`'s drift logic because it doesn't attempt drift detection at all — it's a simpler, single-number accuracy summary meant (per its own docstring) "so teammates can verify the trust engine is computing it correctly," which is itself telling: it exists as an informal cross-check against a trust engine its author didn't have visibility into at build time.

### 4. Her enums vs. `main`'s — naming difference or different model?

| Her enum | Main's closest equivalent | Verdict |
|---|---|---|
| `SimulationPhase` (`GOOD`/`DEGRADED`/`RECOVERY`) | *(none — no equivalent in `main`'s `shared/enums.py` at all)* | Not an overlap. A genuinely new, legitimately simulator-local concept (which invoice-difficulty phase is active) that main's `shared/` never needed because it has no simulator yet. Belongs in a simulator-local module post-port, not `shared/` |
| `DriftDirection` (`DEGRADING`/`RECOVERING`) | `DriftSeverity` (`NONE`/`WARNING`/`CONFIRMED`/`CRITICAL`) | **Different model, not a naming difference.** `DriftDirection` is binary (which way is accuracy moving); `DriftSeverity` is a 4-state confidence ladder tied to ADR-0006's two-stage tripwire-then-z-test methodology (a tripwire alone gets you `WARNING`; a confirmed z-test gets you `CONFIRMED`; a critical error short-circuits straight to `CRITICAL`). You cannot map `DEGRADING`→one severity value, because "degrading" could be `WARNING` (unconfirmed) or `CONFIRMED` or `CRITICAL` depending on statistical power and error type — the direction alone doesn't carry that information. A `DriftDirection`-style label could still exist as a *display-only* derived annotation (`recent_accuracy < baseline_accuracy`) computed from `DriftResult`'s existing fields, but it isn't a rename target for `DriftSeverity` itself |
| `ApprovalStatus` (`PENDING`/`APPROVED`/`REJECTED`) | `RecommendationStatus` (`PENDING`/`APPROVED`/`REJECTED`/`SUPERSEDED`) | **Closest of the three to a real naming difference** — 3 of 4 values match exactly in name and meaning. The one gap is `SUPERSEDED` (a recommendation invalidated by a newer one before a human ever ruled on it), which her model has no equivalent state for. This one is close to a straight rename with one new case to handle, not a redesign |

### 5. `api_client.py` — endpoints called, vs. `docs/lanes/vp.md`'s real list

*(The brief named `docs/lanes/backend-lane-context.md`; no file by that name exists — `docs/lanes/vp.md` is the backend lane primer that carries the endpoint list, at `vp.md:125-142`, and is what this comparison uses.)*

| Her endpoint | Real equivalent (`vp.md`) | Match? |
|---|---|---|
| `GET /agents` | `GET /api/v1/agents` | Shape matches (list agents) |
| `GET /agents/{id}` | `GET /api/v1/agents/{agent_id}` | Shape matches |
| `GET /agents/{id}/decisions` | `GET /api/v1/decisions` (global, filterable — not nested under agent) | **No match** — different resource shape (nested vs. flat+filter) |
| `GET /agents/{id}/autonomy-history` | `GET /api/v1/agents/{agent_id}/trust/history` | Close, different path and — critically — hers returns tier-limit events, the real one returns trust-evaluation history |
| `GET /approvals`, `POST /approvals/{id}/resolve` | `GET /api/v1/recommendations`, `POST /api/v1/recommendations/{rec_id}/approve`, `POST /api/v1/recommendations/{rec_id}/reject` | **No match** — she has one generic "resolve with a status body" endpoint; the real API has two distinct action endpoints, and operates on `Recommendation` not `HumanApproval` |
| `GET /audit` | `GET /api/v1/audit-log` | Close (name differs, shape probably close) |
| `GET /invoices/{id}`, `POST /invoices` | *(no equivalent — closest is `POST /api/v1/decisions`)* | **No match, and conceptually inverted** — her API asks the backend to *decide* on a submitted invoice (`SubmitInvoiceResponse.policy_decision`); the real architecture has the simulator's own agent decide first, then POST the completed decision to `/decisions` for the backend to check against the agent's limit and log. This is the same self-limiting-agent issue from Q2, showing up again at the API boundary |
| `POST /simulation/runs`, `GET /simulation/runs/{id}`, `GET /simulation/runs` | `POST /api/v1/simulation/runs`, `GET /api/v1/simulation/runs/{run_id}` | **Matches structurally** — the one endpoint family that lines up almost exactly |

**Score: 1 of 8 endpoint groups matches cleanly (simulation runs); 2 are close-but-wrong-shape (agents, audit); 1 partially matches (agent detail); the rest — approvals and invoices, which are the two most demo-critical flows — have no real counterpart and reflect a different mental model of who decides what.**

### 6. The 97 tests — LOCAL/RENAME vs. REWRITE

| Test file | Tests | Bucket |
|---|---:|---|
| `test_generator.py` | 24 | Likely survive (RENAME) — zero hits for tier vocabulary in a targeted search; these specifically test seeding/reproducibility/vendor-pool/date logic, not the boundary-case branch |
| `test_scripted_agent.py` | 13 | Need rewriting (REWRITE) — the file itself doesn't name tier constants, but every test calls `ScriptedAgent.decide()`, which is REWRITE; behavioral properties (determinism, confidence-on-error) are worth re-asserting, exact expected values are not portable |
| `test_error_rate_validation.py` | 9 | Need rewriting (REWRITE) — exercises `ScriptedAgent` + `GroundTruthLabeller`, both REWRITE; the *validation goal* (good-phase error rate materially lower than degraded-phase) should be re-run post-port, this file's assertions will not survive as-is |
| `test_labeller.py` | 25 | Need rewriting (REWRITE) — directly asserts tier-limit-based rule outcomes |
| `test_runner.py` | 19 | Need rewriting (REWRITE) — essentially entirely about `wilson_lower_bound()`, which is deleted per ADR-0010 |

**Roughly 24 of 90 collected test functions (about a quarter, and the least interesting quarter — reproducibility/plumbing tests) are LOCAL/RENAME and likely survive close to as-is. The other ~66 (including all the tests that actually validate the interesting behaviour — error rates, rule outcomes, Wilson bounds) are REWRITE-coupled and need to be rewritten alongside the code they test**, not after.

### 7. `frontend/src/` — 3-tier/hand-written-types dependency vs. structural survivors

**Depend on the 3-tier model or `types/api.ts` (REWRITE, 1,980 lines total):** both `agents/` pages, `approvals/page.tsx`, `audit/page.tsx`, `simulation/page.tsx`, `AccuracyGauge.tsx`, `HorizontalThresholdGauge.tsx`, `ApprovalRow.tsx`, `AutonomyLadder.tsx`, `api-client.ts`, `mocks/data.ts`, `mocks/handlers.ts`, `types/api.ts` itself.

**Structural, survive regardless (LOCAL, 511 lines total):** `app/page.tsx`, `app/layout.tsx`, `app/globals.css`, `Icons.tsx`, `Providers.tsx`, `Sidebar.tsx`, `query-client.ts`, `mocks/browser.ts` — routing shell, font/CSS setup, the TanStack Query client config, the MSW bootstrap, and the icon set. None of these import a domain type at all.

**The one genuine surprise: `AutonomyTimeline.tsx` (241 lines) and `InvoiceCard.tsx` (73 lines) are RENAME, not REWRITE** — the timeline chart in particular is generic enough (driven purely by numeric/enum fields on whatever event type it's handed) that it's a real head start on the single most important chart in the product, not a casualty of the divergence.

---

## Totals

| Classification | `simulator/` lines | `frontend/src/` lines | Total | % of scope |
|---|---:|---:|---:|---:|
| RENAME | 828 | 314 | 1,142 | 5.8% |
| REWRITE | 2,120 | 1,980 | 4,100 | 20.8% |
| LOCAL | 175 | 511 | 686 | 3.5% |
| DISCARD | 13,780 | 0 | 13,780 | 69.9% |
| **Total** | **16,903** | **2,805** | **19,708** | 100% |

The DISCARD number is dominated by the three fixture JSON files (12,743 of 13,780 lines, 92%) — generated data, not authored logic, and cheap to regenerate once the generator/labeller are fixed. Excluding fixtures and the lockfile, the code that's actually in play is **828 (simulator RENAME) + 2,120 (simulator REWRITE) + 314 + 1,980 (frontend) + 175 + 511 (LOCAL, both) ≈ 5,928 lines** — a much smaller number than "35,600 lines" suggests, because the bulk of that original figure was fixtures and a `package-lock.json`/`nexttemp/` scaffold that were never going anywhere regardless of this decision.

## Person-day estimate

**Port (repoint the existing code at `main`'s real `shared/`), for someone already fluent in this codebase and in the real contracts:**

- Mechanical RENAME pass across ~1,142 lines (simulator + frontend), re-run tests after each file: **~1 day**
- `labeller.py` + `scripted.py` rule-table rewrite (collapse tier×category → single rung, re-derive rule 6-8/7/8 boundaries): **~0.75 day**
- `generator.py` boundary-case generation rewrite (2 methods) + `runner.py` (delete duplicate Wilson, import `trust`'s): **~0.75 day**
- `llm.py` prompt rewrite + a validation pass against real Gemini calls (this step has external-dependency risk, see "biggest unknown" below): **~0.5 day**
- `api_client.py` + `mocks/handlers.ts` rewrite against the real 18-endpoint surface — **blocked on `backend/openapi.json` existing**, which per the state audit doesn't exist yet; the coding itself is **~1 day** once that surface is real
- Frontend domain components (`AutonomyLadder`, `AccuracyGauge`, `HorizontalThresholdGauge`, `ApprovalRow` — including building the missing `AgentOpinion`/dissent display `ApprovalRow` currently lacks entirely) + `types/api.ts` + `mocks/data.ts`: **~1.5 days**
- Frontend pages wiring (5 pages) to the rewritten data layer: **~1 day**
- Test rewrites (`test_labeller`, `test_runner`, `test_error_rate_validation`, `test_scripted_agent` — 66 tests): **~1 day**
- Fixture regeneration + integration pass (`generate` all 3 phases, smoke-test, full `pytest`/`tsc`/`build` re-run): **~0.5 day**

**Port total: ≈ 7-9 person-days.**

**Rebuild from scratch, using her version purely as a design reference (no code reuse, direct implementation against real `shared/`):** loses the ~1,142 RENAME-free lines and the ~511+175 LOCAL lines that would otherwise transfer with near-zero effort (vendor pools, distributions, cache, protocol, routing shell, MSW/query plumbing, the icon set) — all of that has to be typed out fresh, even while visually copying her structure. Offsetting that, a from-scratch build skips the "understand her Pydantic model, then unwind it" comprehension tax on the REWRITE-classified files. Net: **≈ 10-13 person-days** — meaningfully more than the port, not dramatically more.

## Recommendation: **partial port**

Port outright (RENAME + LOCAL, ~1,828 lines, ~1-1.5 days): `agents/base.py`, `agents/cache.py`, `distributions.py`, `cli.py` (with the Wilson import fix), `__main__.py`, `test_generator.py`, and on the frontend side `AutonomyTimeline.tsx`, `InvoiceCard.tsx`, and the entire structural shell (`layout.tsx`, `globals.css`, `Icons.tsx`, `Providers.tsx`, `Sidebar.tsx`, `query-client.ts`, `mocks/browser.ts`, `app/page.tsx`).

Rewrite in place, using her version as the working reference rather than starting blank (REWRITE, ~4,100 lines, ~6-7.5 days): everything touching the tier/category limit table (`labeller.py`, `scripted.py`, `llm.py`'s prompt, `generator.py`'s boundary logic), everything touching the invented API surface (`api_client.py`, `mocks/handlers.ts`, `mocks/data.ts`, `types/api.ts`), and the ladder-facing UI (`AutonomyLadder.tsx`, `AccuracyGauge.tsx`, `HorizontalThresholdGauge.tsx`, `ApprovalRow.tsx` — the last of these also needs new functionality, not just new types, to surface governance dissent per `docs/lanes/ad.md`).

Discard outright: the 3 fixture JSON files, `uv.lock`, and (already flagged in the state audit, same verdict here) `frontend/nexttemp/`.

This is cheaper than a from-scratch rebuild by something like 2-4 person-days, concentrated almost entirely in the parts of the codebase that were never actually wrong in the first place — invoice generation realism, the cache mechanism, and (unexpectedly) the autonomy timeline chart.

## Biggest unresolved unknown

**Whether the team has working Gemini API access, and what the LLM agent's real error behaviour looks like once repointed at the real ladder.** `llm.py` raises `EnvironmentError` without a `GEMINI_API_KEY` (`:145-148`) — nothing in the code or either audit confirms a key exists, has quota, or that `gemini-2.5-flash` (`shared/constants.py`'s `GEMINI_MODEL` on her branch) behaves as the "genuinely harder degraded-phase invoices produce genuinely more LLM mistakes" design assumes once the prompt is rewritten against 5 flat rungs instead of 15 tier×category cells (which may change how "boundary case" reads to the model, in either direction). This can't be resolved by reading the diff — it only surfaces once someone runs the rewritten `llm.py` against live Gemini calls, and until then the ~20%-degraded-phase-error-rate claim central to the demo's drift-detection beat is unverified for the ported version specifically (her original 97 passing tests exercise `ScriptedAgent`, not `GeminiAgent`, precisely because live LLM calls aren't run in CI — so "97 tests pass" was never evidence about this either).
