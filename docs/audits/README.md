# Audits — what is here, and what is cited but missing

Point-in-time reviews of the repo's real state. Each one is a snapshot, not a
living document: a finding in an August audit describes August, and later
entries in `docs/DECISION_LOG.md` are what say whether it was fixed.

## Committed

| File | Date | Covers |
|---|---|---|
| `2026-08-21-pre-merge-audit.md` | 21 Aug | State before the first cross-lane merge |
| `2026-08-23-port-feasibility.md` | 23 Aug | Whether the divergent simulator/frontend branch could be ported |
| `2026-08-23-state-audit.md` | 23 Aug | Repo state after the contract freeze |
| `2026-08-27-delta-audit.md` | 27 Aug | What changed in the four days after |
| `2026-08-31-state-audit.md` | 31 Aug | The last committed audit |

## Cited but never committed

Three audits are referenced across `docs/CONTEXT.md` and
`docs/DECISION_LOG.md` and **do not exist in this repository**. Anyone
following one of those citations will find nothing.

| File | Times cited | Cited as the source for |
|---|---|---|
| `2026-09-02-frontend-audit.md` | 2 | The frontend's client-side threshold finding |
| `2026-09-06-audit.md` | 5 | The freeze-cleanup cooldown bug, the concurrency races, the simulation-runs stub |
| `2026-09-08-freeze-audit.md` | 3 | Per-person outstanding work going into the freeze; stale counts in `CONTEXT.md`'s status table |

**This does not mean the findings are invented.** Every fix those citations
support is independently verifiable in this repo: the decision-log entry
beside each citation describes the defect and the change, the code is in the
commit that entry names, and each has tests pinning the behaviour. The
concurrency races have `backend/tests/test_race_conditions.py`; the cooldown
bug has its own test in `backend/tests/test_recommendations.py`; the
simulation-runs work has `backend/tests/test_simulation.py`. The audits were
the *route* to those findings, not the evidence for them.

What is genuinely lost is the provenance trail — the reasoning and the
measurements taken at the time, which lived only in those files.

**If you are reviewing this project:** treat a claim citing one of the three
as supported by the code and tests it names, not by the missing document. If
you are on the team and still hold a copy of any of them, commit it and delete
its row from this table.

Recorded 2026-09-14 rather than quietly rewriting the citations, so the gap
stays visible instead of being smoothed over.
