# ADR-0001: Statistical evidence, not LLM judgment, drives autonomy decisions

## Status

Accepted

## Context

The system needs to decide, over time, whether an AI invoice-approval agent
has earned a higher spending limit. There are two fundamentally different ways
to answer "has this agent been performing well?":

1. Ask an LLM to look at the agent's recent decisions and judge whether it's
   trustworthy.
2. Compute it — accuracy, error rates, agreement with human rulings — as
   arithmetic over the decision log, with confidence bounds attached.

This is a money-moving system in a compliance-sensitive domain (the project's
own framing explicitly imagines being asked to justify a decision "before a
judge"). Whatever produces the number that gates real financial authority has
to be reproducible, explainable without appeal to a model's internal state,
and stable under audit.

## Decision

Whether an agent's autonomy limit should change is answered by pure statistics
over its decision history — Wilson-bound accuracy, critical-error rate,
drift-detection z-tests — computed in `trust/trust_engine/`, a lane that is
hard-ruled to contain **no LLM calls, no network calls, and no framework
dependencies** (FastAPI, DB, Redis, Celery are all explicitly forbidden there).
LLM reasoning (via LangGraph + Gemini in `vc/governance`) is used only to
*explain* what the statistics already established — to produce a
human-readable recommendation — never to originate the evidence itself.

## Consequences

- Every trust score and drift flag is reproducible from the same decision log,
  by anyone, without re-running a model. Two people (or a person and a judge)
  looking at the same history get the same number.
- The trust engine can be fully unit- and property-tested (113 tests, 112
  passing as of this writing) with exact numeric assertions — something not
  possible if the "is this agent trustworthy" question were answered by an
  LLM call.
- It creates real integration overhead: two lanes (`trust`, `governance`) have
  to agree on a contract (`TrustEvaluation`, see ADR-0005) instead of one lane
  doing everything end to end.
- It means the LLM layer can be swapped, prompted differently, or fail
  outright without touching what actually gates the agent's autonomy — the
  blast radius of an LLM mistake or hallucination is contained to the
  explanation, not the decision.

## Alternatives considered

- **LLM directly scores/grants autonomy.** Rejected: not reproducible (same
  history, different day, potentially different score), not something you can
  defend line-by-line under audit, and vulnerable to prompt injection via
  invoice content the agent itself is evaluating.
- **Hybrid score (LLM opinion blended numerically with statistics).** Rejected:
  blending an unreproducible signal into a number that's supposed to be
  auditable evidence just moves the reproducibility problem one level down
  instead of removing it, and makes the resulting number harder to explain,
  not easier.
- **No LLM at all, pure rules engine end to end.** Considered and rejected for
  the opposite reason — a pure rules engine can enforce and can compute, but
  can't produce the human-readable rationale a reviewer needs to understand
  *why* a recommendation was made; that's a genuinely separate job, which is
  why `vc/governance` exists as its own lane.
