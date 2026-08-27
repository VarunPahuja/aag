# ADR-0011: One pagination envelope, and a mandatory `reason` on every state-changing endpoint

## Status

Accepted

## Context

`backend/`'s HTTP contract (docs/lanes/vp.md, docs/DEADLINES.md: Tue 25 Aug)
covers eighteen endpoints across five resources — agents, decisions,
recommendations, audit samples, and simulation runs. Two shapes recur across
all of them: every `GET` that returns more than one item needs a list shape,
and every `POST` mutates something. Left undecided per-endpoint, five
resources means five independent chances to drift: one list response with
`items`/`total`, another with `results`/`count`; one mutation that asks for
a justification, another that doesn't because nobody thought to ask. Once
the frontend generates types from `backend/openapi.json` and starts
building against them, correcting an inconsistency means a breaking change
to a contract another lane already depends on. Deciding both shapes once,
before any endpoint ships, is cheaper than reconciling five ad hoc ones
later.

## Decision

**One pagination envelope, on every list endpoint, no exceptions:**

```json
{ "items": [...], "total": 0, "page": 1, "page_size": 20 }
```

`items` is the page's contents; `total` is the full matching count,
independent of page size, so a client can compute "page 3 of 7" without a
second request. No endpoint ever returns a bare JSON array. Implemented
once as a generic `Page[T]` (`backend/app/schemas/envelope.py`) and a
`paginate()` helper (`backend/app/api/v1/pagination.py`) every list route
calls, rather than five hand-rolled shapes.

**Every state-changing endpoint requires a non-empty `reason` string in its
request body — no exceptions, including the ones that don't look like
governance decisions at face value:**

| Endpoint | Why `reason` still applies |
|---|---|
| `POST /recommendations/{id}/approve`, `.../reject` | The clearest case — this is the human-authorization step ADR-0004 exists for. An approval with no stated reason defeats the point of requiring a human at all. |
| `POST /audit-samples/{id}/review` | The reviewer's finding *is* evidence (ADR-0009); recording only a verdict and not why discards the part a future audit would actually want to read. |
| `POST /decisions` | Not a governance decision, but still a mutation — the ingesting caller (the simulator today, a real agent integration later) states why this decision is being submitted (which batch, which run). |
| `POST /simulation/runs` | An operational action, not an authorization, but it still starts something and consumes resources — same rule, no carve-out for "this one's just infrastructure." |

Implemented as a `reason: str = Field(min_length=1, ...)` field on every
mutation's request schema (`backend/app/schemas/{decision,governance,audit,simulation}.py`);
FastAPI's request validation rejects an empty or missing reason with the
standard `422` error shape before the route body ever runs.

Both decisions compose with the third cross-cutting rule this branch
establishes: one error body everywhere (`code`, `message`, `detail`,
`backend/app/errors.py`) — a client that understands the envelope and the
error shape understands every endpoint in the API, not just the one it
read the docs for first.

## Consequences

- A client library (or a generated TypeScript client) writes pagination
  and mutation-reason handling exactly once, not five times with five
  subtle inconsistencies to reconcile.
- `reason` is at present just a string the stub stores nowhere — it is not
  yet persisted, not yet surfaced in the audit log, and no endpoint
  currently validates its *content* beyond non-emptiness. Persisting it is
  explicitly Fri 28 Aug / Mon 31 Aug work (docs/DEADLINES.md), not this
  branch's — the contract asks for it now so nothing downstream has to add
  a breaking field later.
- Requiring `reason` on `POST /decisions` and `POST /simulation/runs` is a
  real ergonomics cost on what are otherwise machine-to-machine calls (the
  simulator posting hundreds of decisions per run). The alternative —
  carving out an exception for "operational" mutations — was rejected (see
  below), so this cost is accepted deliberately, not overlooked.
- `page_size` has no server-enforced ceiling beyond the `le=200` validation
  on the query parameter (`backend/app/api/v1/pagination.py`) — a caller
  cannot request an unbounded page, but 200 is an arbitrary number chosen
  for a capstone's data volumes, not a value load-tested against anything.

## Alternatives considered

- **No pagination envelope — return a bare array, put `total` in a response
  header (`X-Total-Count`).** Rejected: headers are invisible to a
  generated TypeScript client's response type, so `total` would be
  effectively undiscoverable without reading this ADR. A body-only
  contract needs no side channel to be complete.
- **`reason` only on `approve`/`reject`, not on the other three mutations.**
  This was the first draft. Rejected once `POST /decisions` was considered
  directly: docs/lanes/vp.md's own framing — "this is a governance system;
  unexplained mutations are what it exists to prevent" — does not
  distinguish "a human authorized something" from "the system recorded
  something," and drawing that line per-endpoint is exactly the kind of
  five-independent-decisions drift this ADR exists to avoid. Applying the
  rule uniformly costs a little ergonomics on the machine-to-machine paths
  and buys not having to defend an inconsistent boundary to a panel later.
- **A cursor-based pagination envelope (`next_cursor`/`prev_cursor`)
  instead of `page`/`page_size`.** Rejected for this project's scale — cursor
  pagination solves a stability problem (items shifting between pages under
  concurrent writes) that a capstone demo with a handful of agents and a
  bounded decision volume does not have. `page`/`page_size` is simpler to
  generate a type for and simpler for the frontend to build a page-number
  control against.
