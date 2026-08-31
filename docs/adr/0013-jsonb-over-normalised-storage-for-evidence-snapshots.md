# ADR-0013: JSONB over normalised storage for evidence snapshots

## Status

Accepted

## Context

Two tables in `docs/lanes/vp.md`'s schema hold data with real internal
structure: `trust_evaluations.payload` is a complete `shared.contracts
.TrustEvaluation` — `ProportionResult`s for accuracy/agreement/utilization,
a `DriftResult`, a tuple of `ScoreComponent`s, reason codes — and
`recommendations.agent_opinions` is the full panel of four
`shared.contracts.AgentOpinion`s a governance run produced. Both could be
normalised: a `trust_evaluation_components` table with one row per
`ScoreComponent`, an `agent_opinions` table with one row per `AgentOpinion`
and a foreign key back to `recommendations`, and so on down through
`DriftResult`'s ten fields.

Nothing in this project ever queries *inside* either structure. No endpoint
in `backend/openapi.json` filters trust evaluations by a single score
component's value, or recommendations by one dissenting agent's confidence.
Every consumer — `GET /agents/{id}/trust`, `GET /recommendations/{id}`, the
frontend's evidence panel, an auditor reading a decision's context — reads
the whole structure back and renders all of it at once. That is the
definition of an evidence snapshot: a fact about a point in time, not a set
of independently queryable records.

## Decision

Store `trust_evaluations.payload` and `recommendations.agent_opinions` as
`JSONB` (`app/models/types.py:JSONBType` — Postgres `JSONB`, with
`.with_variant(sa.JSON(), "sqlite")` so the same model also runs against the
throwaway SQLite database `backend/tests/test_alembic_migration.py` and
`backend/tests/test_seed.py` use, since no Postgres service exists in CI
(`.github/workflows/ci.yml`) or is guaranteed on every contributor's machine).
The four scalar columns that sit alongside `trust_evaluations.payload`
(`trust_score`, `recommended_limit`, `direction`, `evaluated_at`,
`app/models/trust_evaluations.py`) are pulled out specifically because those
*are* queried and sorted on — a listing or a chart needs `ORDER BY
evaluated_at DESC` and `WHERE direction = 'INCREASE'` without unpacking JSON
first. Everything else about an evaluation stays inside the blob.

## Consequences

- Writing a `TrustEvaluation` or a tuple of `AgentOpinion`s is one `INSERT`
  with one JSON-serialised column, matching exactly how the trust and
  governance lanes already hand these values across: as one complete
  dataclass instance, never field by field (`shared/contracts.py`).
- Reading one back for display is one row fetch, not a join across
  `trust_evaluations` + `score_components` + `drift_results`. The frontend's
  evidence panel (`docs/lanes/vp.md`) wants exactly this shape already.
- The cost: Postgres cannot enforce `TrustEvaluation`'s own invariants (e.g.
  `rung_of(current_limit) == current_rung`, documented on the dataclass
  itself) *inside* the JSONB blob the way `ck_agents_rung_matches_limit`
  enforces it on `agents` (`app/models/agents.py`). Anyone who queries this
  data outside the ORM path that produces it (a raw SQL report, a future
  analytics job) inherits whatever shape was written, unchecked by the
  database. This is accepted because nothing in the current design writes to
  these columns except the code paths that already construct a real
  `TrustEvaluation`/`AgentOpinion` dataclass first (fixtures
  (`app/fixtures/trust.py`, `app/fixtures/recommendations.py`) and the seed
  script (`app/seed.py`) both build the dataclass, then serialise it — never
  a hand-typed dict).
- `JSONB` supports indexing (`GIN`) and containment queries
  (`payload @> '{"direction": "INCREASE"}'`) if a future requirement needs
  one, without a schema migration — the escape hatch this ADR's alternative
  (plain `JSON`) does not offer as cheaply on Postgres.

## Alternatives considered

- **Fully normalised storage** (`score_components`, `agent_opinions` as
  proper foreign-keyed tables). Rejected: costs a migration and an ORM
  relationship per nested dataclass field (`ProportionResult` appears three
  times per `TrustEvaluation`; `DriftResult` has ten fields), for a query
  pattern — filtering or aggregating on one nested field — nothing in this
  project's endpoints or frontend design does. `docs/lanes/vp.md` already
  names this exact tradeoff and calls it out as "a deliberate decision worth
  an ADR"; this is that ADR.
- **Plain Postgres `JSON`, not `JSONB`.** Rejected: `JSON` stores the exact
  input text and re-parses it on every access; `JSONB` stores a decomposed
  binary form that is faster to query and supports indexing. Since the
  `.with_variant(sa.JSON(), "sqlite")` fallback already means "the exact
  Postgres type" isn't guaranteed identically across every environment this
  code runs in, there is no reason to give up `JSONB`'s advantages on the one
  environment (production, `docker-compose.yml`) that actually has it.
- **A hybrid: normalise only the fields most likely to be queried later
  (e.g. `critical_errors`, `trust_score`).** This is effectively what was
  chosen — `trust_score`, `recommended_limit`, `direction`, `evaluated_at`
  are already their own columns. Going further (pulling out
  `critical_errors`, `total_decisions`, etc.) was rejected for now: nothing
  in `backend/openapi.json` currently needs to filter or sort on them, and
  each one pulled out is a field that can silently drift from the JSONB copy
  if a future write path updates one without the other. Revisit via a new
  ADR if a real query need appears.
