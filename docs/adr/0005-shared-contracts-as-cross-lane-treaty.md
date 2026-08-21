# ADR-0005: `shared/` as a cross-lane treaty, not a library each lane can fork

## Status

Accepted

## Context

Four people own four independently-developed lanes (backend, trust, governance,
simulator/frontend) that nonetheless have to agree on exactly what a
`DecisionRecord` or a `TrustEvaluation` looks like — field for field, type for
type. Two ways to get that agreement: a single shared definition all four
lanes import directly, or each lane defines its own local shape and something
at the boundary translates between them.

## Decision

One shared Python package, `shared/`, holds the cross-lane types (`contracts.py`),
enums (`enums.py`), constants (`constants.py`), and reason codes
(`reason_codes.py`). Every lane imports these directly — no lane redefines its
own version. Each file's own docstring calls itself a **"TREATY FILE — changes
require all four reviewers"** (`shared/constants.py:1`, `shared/contracts.py:1`,
`shared/enums.py:1`, `shared/reason_codes.py:1`). `CONTRIBUTING.md` codifies
this as an actual review requirement, not just a comment.

Plain dataclasses were chosen over Pydantic or an ORM base class
specifically so the trust engine — which is hard-ruled to be importable with
nothing but the standard library — can depend on `shared/` without pulling in
a web framework (`shared/contracts.py:3-6`).

## Consequences

- Every lane gets compile-time (well, import-time) certainty that the field
  names and types they're passing around match what every other lane expects
  — no silent drift between "what the trust engine emits" and "what the
  backend expects to receive," *as long as everyone actually uses the shared
  type*.
- The four-reviewer requirement is real friction: a one-line field rename
  becomes a four-person review, deliberately, because the brief for
  `reason_codes.py` states renaming a code "silently breaks whatever reads
  it" (`shared/reason_codes.py:8`) — the cost of getting a treaty file wrong
  is paid by every lane, not just the one that changed it.
- **This tradeoff has already misfired once**, which is direct evidence for
  why the rule exists: `trust/trust_engine/score.py:53-58` defines a local
  `ScoreResult` dataclass that duplicates most of `TrustEvaluation`'s scoring
  fields under different names (`renormalised` vs. `weights_renormalised`)
  instead of returning `TrustEvaluation` itself. Nothing enforces the treaty
  at the type-checker or CI level — it's currently only a convention — so a
  lane can drift into an incompatible parallel shape without anyone noticing
  until integration.
- A related, harder-to-see version of the same failure already happened at
  the branch level: `uk/trust` was built against an empty placeholder
  `shared/contracts.py` because its branch and the branch that actually
  populated the treaty files (`uk/shared-trust-contracts`) diverged from the
  same base commit without either being merged into the other (see
  `DECISION_LOG.md`). A shared package only enforces agreement if everyone is
  actually building against the same commit of it.

## Alternatives considered

- **Per-lane local types + an adapter/anti-corruption layer at each
  boundary.** Rejected: decouples lanes (each can evolve its internal shape
  freely) but trades that for translation code at every boundary that itself
  needs to stay in sync — for a four-person team on a fixed deadline, that's
  more code to write and more places for the exact same drift to happen, just
  moved one layer over instead of prevented.
- **A schema-first approach** (e.g. JSON Schema or Protobuf, generating
  per-language types). Rejected as overkill: all four lanes are Python in a
  single repo; there's no cross-language boundary to justify the extra
  tooling, and it would still need the same four-reviewer discipline on the
  schema files themselves.
- **Pydantic models instead of plain dataclasses**, for the free validation.
  Rejected specifically because it would force a hard dependency on Pydantic
  into the trust engine, which is deliberately kept framework-free
  (`shared/contracts.py:3-6`) so it stays trivially testable and embeddable
  anywhere.
