# ADR-0008: One monorepo, in-process library calls, not four microservices

## Status

Accepted

## Context

Four lanes, four owners, and a genuine architectural boundary between them
(ADR-0001) could plausibly be built as four independently deployable services
talking over the network, or as four packages in one repository that get
wired together in-process inside a single deployable backend. This is a
capstone project with a fixed deadline (2026-09-15) and a four-person team —
the choice has real cost either way: services buy independence, a monorepo
buys speed and simplicity.

## Decision

AAGP is one repository containing four Python/TypeScript packages
(`backend/`, `trust/`, `governance/`, `simulator/` + `frontend/`), deployed via
a single `docker-compose.yml`, not four independently deployed services. The
trust engine in particular is built as an installable local package
(`trust/pyproject.toml`, `[tool.hatch.build.targets.wheel] packages =
["trust_engine"]`) meant to be **imported directly**, not called over a
network — which is exactly why it is hard-ruled to have zero FastAPI, zero
network calls, and zero framework dependencies (`docs/CONTEXT.md`, trust lane
hard rules; enforced in practice, verified by grep across
`trust/trust_engine/` finding only stdlib and `shared`/`trust_engine` imports).
If the trust engine were its own deployed service, that hard rule would make
no sense — a service needs a way to be *called*.

## Consequences

- The backend calls into the trust engine as a plain Python function call,
  not an HTTP/gRPC round trip — no serialization boundary, no network
  failure mode, no separate deployment to keep in sync with the backend's
  version of `shared/`.
- All four lanes share one `shared/` treaty package by filesystem import
  (ADR-0005) rather than by publishing and versioning a package across
  service boundaries — simpler for a four-person team on a five-week clock,
  at the cost of not being able to deploy or scale any one lane independently
  of the others.
- `docker-compose.yml` (currently empty, `vp/backend`'s responsibility) is
  the intended single entry point for running the whole system locally —
  there's no per-lane deployment story to design or maintain.
- Cost: the strict lane boundaries (no FastAPI in `trust/`, etc.) have to be
  enforced by convention and code review, not by an actual network boundary
  that makes violations impossible — a monolith makes it *easy* for a
  future contributor to accidentally reach across a lane boundary (e.g. import
  something backend-specific into `trust/`) since nothing but discipline stops
  it. This is the same enforcement gap noted in ADR-0005 for the shared
  contracts.
- If the project ever needed independent scaling (e.g. the trust engine
  computing evaluations for many agents under load separately from the API
  serving traffic), this decision would need revisiting — it is explicitly
  scoped to prototype/capstone needs, not a production scaling target (see
  Non-goals in `docs/CONTEXT.md`).

## Alternatives considered

- **Four independent microservices**, each with its own deployment, each lane
  exposing an API the others call. Rejected for this project's scope: four
  network boundaries to design, secure, and keep contract-compatible is
  disproportionate overhead for a single-demo-environment capstone with a
  fixed deadline, and it would directly conflict with the trust engine's hard
  rule against network calls and frameworks — that rule exists *because* the
  engine is meant to be embedded, not served.
- **A single undifferentiated codebase** (no lane boundaries at all, one
  package). Rejected: this is what the four-owner branch structure and
  `shared/` treaty (ADR-0005) exist specifically to prevent — without
  separate packages and hard import rules, the LLM-reasons /
  statistics-provide-evidence / policy-enforces separation (ADR-0001) has
  nothing stopping it from eroding into one tangled service.
- **Monorepo with the trust engine still served over an internal HTTP call**
  (compromise: same repo, but a real network boundary for that one lane).
  Rejected: gains none of a true microservice's independent-deployment
  benefit while still paying the network/serialization cost the pure-function,
  in-process design was chosen to avoid.
