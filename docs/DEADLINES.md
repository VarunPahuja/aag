# Deadlines — Adaptive AI Governance Platform

Submission: **Tuesday 15 September 2026.**
Feature freeze: **Wednesday 9 September 2026.** Nothing new after that date.

Revised 23 August. The previous sheet was never committed to git, so nobody
outside the lead ever saw it. That is the root cause of most of what went wrong
in week one, and it is fixed by this file existing in the repo.

Every item below is binary. It either passes its check or it does not. There is
no "in progress" on this sheet. Report status against the check, not against
effort spent.

Owners: **VP** Varun P. (backend, lead) · **UK** Utkarsh (trust, then simulator)
· **VC** Varun C. (governance) · **AD** Adhya (simulator port, then frontend)

---

## Where we actually are, 23 August

Stated plainly so nobody is planning against a fiction.

| Lane | Reality |
|---|---|
| `shared/` v1.1 | Merged and frozen. **This is the only valid contract set.** |
| Trust engine | Statistical core done, 113 tests green. Ladder, cooldowns, clawback, and `evaluate()` not started (due 26 Aug, on schedule) |
| Backend | Zero lines. OpenAPI missed its 23 Aug date |
| Governance | Zero lines, zero commits since 17 Aug |
| Simulator + frontend | ~35,600 working lines on `ad/simulator-frontend`, 97 tests green, built against an independently-designed `shared/` that is incompatible with `main`. Needs porting, not discarding |
| Docs | Contracts, ADRs, and audits in good shape. Lane briefs and this sheet were untracked until today |

**The `shared/` decision:** `main`'s frozen v1.1 contracts win. The 5-rung
ladder, `DecisionRecord`, and the 18 UPPER_SNAKE reason codes are canonical.
This is not a judgment on the alternative design; the trust engine and eight
ADRs are built on `main`'s version and the rung concept is the product. See
ADR-0010. Do not relitigate this.

---

## Phase 0 — Reset (23-24 Aug)

| Date | Who | Deliverable | Check |
|---|---|---|---|
| Sun 23 Aug | VP | This sheet, lane briefs, ONBOARDING.md committed. `docs/audit-and-risk-fix` merged. Stale docs corrected. ADR-0010 written | Everything referenced in a message to the team actually exists on `main` |
| Mon 24 Aug | VP | Everyone briefed with their lane file and this sheet | Each person has confirmed they read theirs |

## Phase 1 — Foundations (24 Aug - 1 Sept)

| Date | Who | Deliverable | Check |
|---|---|---|---|
| Mon 24 Aug | VC | Start `vc/langgraph-skeleton`. Package config, four agent stubs | Branch exists with a commit |
| Mon 24 Aug | AD | Start `ad/simulator-port`. Type mapping worked out and listed | Mapping posted in the group before code is written |
| Tue 25 Aug | VP | OpenAPI published, all endpoints stubbed, `backend/openapi.json` committed, `export_openapi.py`, staleness check verified | AD can generate types from it without asking a question |
| Wed 26 Aug | UK | `evaluate(decisions, context) -> TrustEvaluation`, ladder, cooldowns, clawback, `ScoreResult` retired | One call returns the full contract. All 18 reason codes reachable, one test each |
| Wed 26 Aug | VC | LangGraph skeleton, 4 nodes, coordinator, stub mode only | Returns a valid `Recommendation` from canned data. Zero LLM calls |
| Thu 27 Aug | AD | Simulator ported onto real contracts, fixtures regenerated, duplicate Wilson deleted | `pytest simulator/` green on `main`'s contracts. Wilson imported from `trust/`, not reimplemented |
| Fri 28 Aug | VP | Alembic migration, all tables, seed script | `make db-reset` produces a seeded database |
| Sat 29 Aug | VP | Policy Engine as a pure module + tests | Invoice + policy version returns allow/escalate + reason code. No DB imports in the module |
| Sat 29 Aug | AD | Frontend types regenerated from `openapi.json`, hand-written `types/api.ts` deleted, `nexttemp/` removed, `typecheck` script added, shadcn/ui added | `npm run typecheck` clean. No hand-written API types remain |
| Sun 30 Aug | VC | Prompt files, structured output parsing, cached mode | Real Gemini responses recorded once and replayed deterministically |
| Mon 31 Aug | VP | Decision ingest endpoint, real persistence, hash-chained audit log | POST a decision, see it in the DB with a valid chain link |
| **Tue 1 Sept** | **All** | **Integration checkpoint 1** | Simulator posts a decision → backend persists → trust evaluates → governance recommends → it appears in the dashboard. Stubs allowed anywhere. **The path must be unbroken** |

## Phase 2 — Build out (2-8 Sept)

| Date | Who | Deliverable | Check |
|---|---|---|---|
| Wed 2 Sept | AD | Agent detail + approvals views on real contracts | Approve/reject flow works, reason field mandatory |
| Thu 3 Sept | VP | Approval workflow endpoints + minimal RBAC | Recommendation approved → policy version created → hard ceiling enforced and visible via `clamped` |
| Thu 3 Sept | VC | Live mode behind a flag, timeout, fallback to cached | Kill the network mid-run and a valid recommendation still comes out |
| Fri 4 Sept | UK | Simulator finalised: phases, degradation injection, deterministic seed | A seeded run reproduces the ten-beat arc identically twice |
| Sat 5 Sept | AD | Charts: trust over time, autonomy step chart on the **5-rung** ladder, accuracy with the Wilson band (Recharts Area behind Line), drift indicator | The Wilson band is visible and narrows as n grows |
| Sun 6 Sept | VP | Audit sampling end to end | Sampled decisions appear in the review queue; a review updates the evidence |
| Mon 7 Sept | AD | Frontend on the real API, mocks retired | No MSW in the running app |
| Tue 8 Sept | All | Full demo runs end to end, no manual intervention | One command, all ten beats |

## Phase 3 — Freeze and harden (9-15 Sept)

| Date | Who | Deliverable | Check |
|---|---|---|---|
| **Wed 9 Sept** | **All** | **FEATURE FREEZE.** Failure cases: LLM down, empty state, insufficient sample, at max rung, hard-ceiling clamp | Each handled visibly, none crash. Anything unmerged at 23:59 is cut |
| Thu 10 Sept | VP | Security pass: RBAC on every mutation, no secrets in the repo. All docs current | Reviewer cannot approve; auditor is read-only. CONTEXT.md matches reality |
| Fri 11 Sept | All | Rehearsal 1, timed, full demo | Under time. Every failure written down |
| Sat 12 Sept | All | Fixes from rehearsal 1. Deck finalised | No open items from rehearsal 1 |
| Sun 13 Sept | All | Rehearsals 2 and 3. Q&A drilling, each person defends their lane | Each person answers 10 questions on their lane without notes |
| Mon 14 Sept | — | **Buffer.** Do not plan work here | Empty on purpose |
| Tue 15 Sept | All | **Submit** | Done |

---

## Standing rules

- Standup message in the group by **11:00 daily**: done / doing / blocked.
  Even when the answer is "nothing yet." Especially then.
- A missed deadline is reported the day before it slips, not the day after.
- `shared/` is frozen until 9 Sept. Any change needs all four to review. If you
  find yourself needing a type that isn't there, stop and ask — do not define
  your own version.
- Always branch off `main`, never off a stale local branch. Run
  `git fetch && git checkout main && git pull` first, every time.
- Feature branches live two days maximum.
- One line in `docs/DECISION_LOG.md` per merged PR.
- Architectural decisions get an ADR **before** the code lands.
- CI must pass before merge. No direct pushes to `main`.

## Backup reviewer

**Utkarsh is backup reviewer.** If VP is unavailable, Utkarsh can approve and
merge anything that does not touch `shared/`. `shared/` still needs all four.

VP has interview commitments between 24 Aug and 3 Sept and will be slow on some
days. Do not sit blocked waiting for a reply — go to Utkarsh.

## Buffer, honestly

There are two genuinely empty days in this schedule: 14 Sept, and the slack
inside Phase 2. If a lane slips more than two days, something gets cut rather
than the freeze moving.

Cut candidates, in the order they should go:

1. Live Gemini mode (cached mode is the demo default anyway)
2. Audit sampling UI (keep the backend, drop the dedicated screen)
3. RBAC beyond a single role check
4. The simulation console (drive runs from the CLI instead)
5. If the frontend port runs long, stop reconciling and rebuild clean against
   real contracts, salvaging only route structure and the MSW pattern

The demo arc, the Wilson band, the clawback, and the approval flow are not
cuttable. They are the project.