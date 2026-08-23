# Backend Lane — AI Context Primer

**Paste this whole file into your AI assistant at the start of a session.**

---

## The project

Four final-year students, capstone prototype for Deloitte USI, due
**15 September 2026**. **Adaptive AI Governance Platform (Earned Autonomy
Engine).**

An AI agent approves invoices. It starts allowed to approve up to ₹500 alone;
larger amounts must be escalated to a human. As it demonstrates reliable
performance backed by sufficient statistical evidence, the system can recommend
raising the limit one rung at a time along ₹500 → ₹1,000 → ₹2,500 → ₹5,000 →
₹10,000. A human approves every increase. If performance degrades, the system
detects it and claws the limit back automatically.

> **LLM reasons. Statistics provide evidence. Policy Engine enforces. Humans
> authorize.**

Full design in `docs/SYSTEM-EXPLAINED.md`. ADRs in `docs/adr/`.

## Lanes

| Lane | Owner | Directory |
|---|---|---|
| **Backend & Policy (this lane)** | **Varun P., team lead** | **`backend/`** |
| Trust & Risk | Utkarsh | `trust/` |
| Governance | Varun C. | `governance/` |
| Simulator | Adhya (port), then Utkarsh | `simulator/` |
| Frontend | Adhya | `frontend/` |

`shared/` is frozen v1.1 and belongs to all four.

---

## This lane's job

The backend is the integration point. Everything else is a library or a client;
this is where they meet, where state lives, and where enforcement happens.

Four responsibilities, in order of how much they matter:

1. **The Policy Engine.** The only thing in the system that decides whether an
   action is permitted. Deterministic, pure, no LLM anywhere near it.
2. **Persistence and audit.** Immutable policy versions, hash-chained audit log,
   a decision record that references the policy in force when it was made.
3. **The HTTP contract.** Every other lane talks through it.
4. **The hard ceiling.** After governance produces a recommendation, plain code
   clamps it to what the statistical evidence supports and records that it did.

### Hard boundaries

- The Policy Engine module imports no database, no network, no LLM. Pure
  functions only. If your AI suggests a DB call inside it, refuse.
- Governance output is advisory. Never apply a `Recommendation` without the
  clamp and without a human approval record.
- Never update `agents.current_limit` without writing a `policy_versions` row in
  the same transaction.
- Never modify `shared/` alone.

---

## Schema

```
users               id, email, role
agents              id, name, current_limit, current_rung, state
invoices            id, amount, vendor, category, submitted_at,
                    ground_truth_action
decisions           id, sequence, invoice_id, agent_id, action,
                    recommended_action, human_ruling, policy_version_id,
                    within_limit, decided_at
policy_versions     id, agent_id, limit, rung, effective_from, created_by,
                    reason, previous_version_id
trust_evaluations   id, agent_id, evaluated_at, trust_score,
                    recommended_limit, direction, payload (JSONB)
recommendations     id, agent_id, trust_evaluation_id, direction,
                    proposed_limit, rationale, agent_opinions (JSONB),
                    status, clamped, clamped_from
approvals           id, recommendation_id, decided_by, verdict, reason,
                    decided_at
audit_samples       id, decision_id, agent_id, sampled_at, reviewed_at,
                    reviewer, verdict, reviewer_action
audit_log           id, ts, actor, actor_type, event_type, entity_type,
                    entity_id, payload (JSONB), prev_hash, hash
```

Three things to be able to defend cold:

**`policy_versions` is append-only and every decision references one.** This is
how "what was this agent allowed to do at 14:00 on 3 September" is answerable
exactly, and how an autonomy change becomes an auditable event with an author
and a reason rather than a mutated column.

**`audit_log` is hash-chained.** Each row stores
`sha256(prev_hash + canonical_json(payload))`. Tampering with history breaks
every subsequent hash. This turns "immutable audit records" from a claim into a
property you can demonstrate live in ten seconds.

**`TrustEvaluation` and agent opinions are stored as JSONB, not normalised.**
They are evidence snapshots, always read whole. Normalising costs days and buys
nothing. This is a deliberate decision worth an ADR.

## Contracts

Read `shared/contracts.py` before writing any Pydantic model. Where a shared
frozen dataclass exists (`TrustEvaluation`, `DriftResult`, `ProportionResult`,
`ScoreComponent`, `Recommendation`, `AgentOpinion`, `AuditSample`,
`DecisionRecord`, `AgentContext`), mirror it field-for-field rather than
inventing a parallel shape, and add a test asserting the field names and types
match so drift is caught in CI.

`shared/constants.py` has `AUTONOMY_LADDER`, `AUTONOMY_FLOOR`, `MAX_RUNG`,
`rung_of()`, `limit_of()`, `SAMPLING_RATE_BY_RUNG`, `sampling_rate_of()`.
`shared/reason_codes.py` has 18 codes. Never write a raw reason string.

---

## Endpoints

```
GET    /api/v1/agents
GET    /api/v1/agents/{agent_id}
GET    /api/v1/agents/{agent_id}/policy-versions
GET    /api/v1/agents/{agent_id}/trust
GET    /api/v1/agents/{agent_id}/trust/history
POST   /api/v1/decisions
GET    /api/v1/decisions
GET    /api/v1/decisions/{decision_id}
GET    /api/v1/recommendations
GET    /api/v1/recommendations/{rec_id}
POST   /api/v1/recommendations/{rec_id}/approve
POST   /api/v1/recommendations/{rec_id}/reject
GET    /api/v1/audit-samples
POST   /api/v1/audit-samples/{sample_id}/review
GET    /api/v1/audit-log
POST   /api/v1/simulation/runs
GET    /api/v1/simulation/runs/{run_id}
GET    /api/v1/health
```

Cross-cutting:
- One pagination envelope everywhere: `items`, `total`, `page`, `page_size`
- One error body everywhere: `code`, `message`, `detail`
- **Every state-changing endpoint requires a reason string.** This is a
  governance system; unexplained mutations are the thing it exists to prevent
- `current_user` dependency reading a header, returning a stubbed user with a
  role (admin / reviewer / auditor). Real JWT later, but the role-check
  decorator exists and is applied from the start
- `backend/openapi.json` is a committed artifact, regenerated by `make openapi`,
  with a CI check that fails when it goes stale

---

## Deliverables

| Date | Deliverable | Check |
|---|---|---|
| Tue 25 Aug | `backend/app/main.py`, all endpoints stubbed, `export_openapi.py`, `openapi.json` committed, staleness check verified | Adhya can generate types without asking a question |
| Fri 28 Aug | Alembic migration, all tables, seed script | `make db-reset` produces a seeded DB |
| Sat 29 Aug | Policy Engine as a pure module + tests | Invoice + policy version → allow/escalate + reason code, no DB imports |
| Mon 31 Aug | Decision ingest, real persistence, hash-chained audit log | POST a decision, valid chain link in the DB |
| Thu 3 Sept | Approval workflow + RBAC | Approval creates a policy version; ceiling enforced and visible via `clamped` |
| Sun 6 Sept | Audit sampling end to end | Sampled decisions in the review queue; a review updates the evidence |
| Thu 10 Sept | Security pass, all docs current | Reviewer cannot approve; auditor read-only |

Order matters: **OpenAPI ships before the database.** The frontend is blocked
until it exists, and the database is not blocking anyone.

---

## Lead responsibilities beyond the code

- Review every PR. Utkarsh is backup when you're unavailable.
- Keep `docs/CONTEXT.md`, `docs/DEADLINES.md`, and `docs/RISKS.md` accurate.
  Stale docs are how week one went wrong.
- Watch for lanes going quiet. Silence is the earliest warning signal you get.
- When someone slips: pair for two hours, then cut scope. Do not build it
  yourself. That is the failure mode that ends with the lead owning three lanes
  and finishing none.

## Instructions for the AI assistant reading this

- Do not write code outside `backend/`.
- Do not modify `shared/`.
- Never put a database call, network call, or LLM call inside the Policy Engine.
- Mirror `shared/` types rather than inventing parallel shapes.
- Do not add Celery, Redis, Prometheus, Grafana, OpenTelemetry, Jaeger, MLflow,
  MinIO, S3, WebSockets, or Kubernetes. All explicitly cut from scope.
- Explain architectural tradeoffs; the human has to defend every decision to a
  technical panel.