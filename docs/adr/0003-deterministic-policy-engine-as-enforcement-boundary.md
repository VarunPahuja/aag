# ADR-0003: A deterministic Policy Engine is the sole enforcement boundary

## Status

Accepted

## Context

Somewhere in this system, something has to be the thing that actually stops
the agent from approving a ₹50,000 invoice when its earned limit is ₹500.
There are two very different places that check could live: inside the agent's
own prompt/instructions, or as a hard, code-level gate the agent's decision has
to pass through regardless of what it "intends" to do.

## Decision

Autonomy limits are enforced by a deterministic **Policy Engine**, owned by
`vp/backend` (`backend/app/policy/`), not by prompting the agent to respect its
own limit. The limit itself (`AUTONOMY_LADDER = (500, 1000, 2500, 5000,
10000)`, `shared/constants.py:16`) is a fixed, shared lookup table, not a
value the agent or an LLM call can set or reason its way around.

## Consequences

- A prompt-injected or simply mistaken agent cannot self-authorize past its
  limit — the check is code, not instruction-following, so it holds
  regardless of what the agent "believes" its limit is.
- Enforcement is independent of and downstream from the trust/governance
  lanes: even if the trust engine's evidence or the governance agent's
  recommendation is wrong, the Policy Engine is what actually has to be wrong
  *and bypassed* for money to move outside the current limit — a second,
  independent layer.
- `AUTONOMY_LADDER` living in `shared/constants.py` rather than inside the
  Policy Engine's own code means the same five rungs are guaranteed to match
  across backend enforcement, frontend display, and simulator invoice
  generation — a rung is one canonical set of numbers, not three
  implementations that can drift.
- Cost: this makes the Policy Engine a hard dependency for *any* end-to-end
  demo — no amount of trust-engine or governance-lane correctness matters if
  nothing enforces the limit, and as of 2026-08-21 the Policy Engine has zero
  code (`backend/app/policy/` is an empty placeholder). This is the most
  consequential absence in the current repo state (see `docs/RISKS.md`).

## Alternatives considered

- **Prompt-based self-limiting** ("you may only approve invoices under your
  current limit, which is ₹X"). Rejected: not enforceable — an LLM can be
  argued out of an instruction, and even absent adversarial input, "the model
  usually follows the rule" is not the same guarantee as "the code makes the
  rule impossible to violate." Unacceptable for a system whose whole premise
  is earning trust through evidence, not assuming it.
- **Enforcement inside the trust engine.** Rejected: the trust engine is
  explicitly hard-ruled to be pure, network-free, and DB-free
  (`docs/CONTEXT.md`, trust lane hard rules) — it has no way to intercept a
  live decision even if it wanted to, and mixing "compute evidence" with
  "block a transaction" would violate the statistics/enforcement separation
  this whole architecture is built around (ADR-0001).
