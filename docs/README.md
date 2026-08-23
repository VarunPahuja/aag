# docs/ — what lives here and when to touch it

This system rots the way every documentation system rots: someone updates the
code and not the doc, because it wasn't obvious which doc to update. This file
exists to make that obvious.

| File | Update it when... | Don't use it for... |
|---|---|---|
| `docs/CONTEXT.md` | The architecture, lane ownership, request flow, or a contract's shape materially changes. It's the front door for anyone new — keep it accurate, not exhaustive. Review it before any `shared/` PR, since the "Shared contracts" section should always match reality. | Day-to-day status updates, in-progress work, or anything that will be stale in a week — that's `DECISION_LOG.md` and `RISKS.md`. |
| `docs/adr/NNNN-*.md` | An architectural decision is made — or an existing one is reversed. Per `CONTRIBUTING.md`, the ADR lands **before** the code that implements it, not as after-the-fact justification. | Recording *that* something changed (that's the decision log) or tracking *whether it's still a risk* (that's the risk register). Never edit a past ADR's Decision/Consequences after it's Accepted — if the decision changes, write a new ADR and set the old one's Status to `Superseded by ADR-NNNN`. |
| `docs/DECISION_LOG.md` | Any merge, decision, or change worth a teammate knowing about — not every commit. One entry, newest at the top: what changed, who, why, what it affects. | Explaining *why* an architectural choice was made in the first place (that's an ADR) — the log records that a change happened, an ADR records the reasoning behind a standing decision. |
| `docs/RISKS.md` | A risk is newly identified, or an existing one changes likelihood/impact/status (opened, mitigated, closed, or materialized). Review at each lane sync, not just when something breaks. | A running to-do list — a risk is something that *might* go wrong, not a task. If it's already scheduled work, it belongs in your task tracker, not here. |
| `docs/audits/YYYY-MM-DD-*.md` | Never edited in place — each is a point-in-time snapshot with the date in its own filename and header. If you need an updated audit, run a new one; it gets its own dated file, it doesn't rewrite an old one. Index below. | Ongoing status (that's `CONTEXT.md`'s Current Status section, which should be kept current going forward). |
| `docs/DEADLINES.md` | The schedule changes — a date shifts, scope gets cut, an owner changes. | Explaining *why* a date changed (that's a `DECISION_LOG.md` entry, and an ADR if it's an architectural cut). |
| `docs/ONBOARDING.md` | The first-time setup steps or the "how we work" rules change. | Current project status — that drifts, and this file shouldn't need touching every week. |
| `docs/SYSTEM-EXPLAINED.md` | The full design, a glossary term, or the reasoning behind a standing architectural decision needs explaining at more length than `CONTEXT.md`'s "keep it accurate, not exhaustive" scope allows. | A substitute for `CONTEXT.md` — that's still the front door; this is the long-form reference behind it. |
| `docs/lanes/*.md` | A lane's boundaries, deliverables, or dates change. Every date in these files must match `docs/DEADLINES.md` — if you change one, check the other. | — |
| `../CONTRIBUTING.md` | The review process itself changes — who has to sign off on what, and the ADR-before-code rule. | Documenting what the code does — that's `CONTEXT.md` and the ADRs. |

### Audit index

| Date | File | Scope |
|---|---|---|
| 2026-08-21 | `docs/audits/2026-08-21-pre-merge-audit.md` | Pre-merge audit of `uk/trust` before the `shared/` contracts merge |
| 2026-08-23 | `docs/audits/2026-08-23-state-audit.md` | Full-repo state audit: branch map, cross-branch divergence (the `shared/` split on `ad/simulator-frontend`), per-lane inventory, per-person briefs |
| 2026-08-23 | `docs/audits/2026-08-23-port-feasibility.md` | File-by-file feasibility probe for porting `ad/simulator-frontend` onto `main`'s contracts — the basis for ADR-0010 and the port estimate in `docs/DEADLINES.md` |

## The one rule that ties it together

If you're about to make a change and can't find which file it belongs in, ask:
*is this a decision, a fact about what happened, or a risk?*

- A **decision** ("we will do X instead of Y, and here's why") → new ADR,
  before the code lands.
- A **fact about what happened** ("X merged, Y landed, Z was found broken") →
  one line in `DECISION_LOG.md`.
- A **risk** ("this could go wrong, or already has, and here's who's on it") →
  a row in `RISKS.md`.

`CONTEXT.md` is the only file that should ever describe *current reality* as a
coherent whole — everything else is either a log of how we got here or a
decision about where we're going.
