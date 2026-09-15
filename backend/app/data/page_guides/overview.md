# Overview — how the whole system works

The Earned Autonomy Engine governs AI agents that approve invoices. An agent starts
with a small spending limit and earns a bigger one only when statistics prove it is
reliable. It never earns one because an AI said so.

## The one sentence
The AI reasons. Statistics provide evidence. The Policy Engine enforces. Humans
authorise increases, and nobody has to authorise a reduction.

## The autonomy ladder
Five fixed rungs: rung 0 ₹500 (the floor), rung 1 ₹1,000, rung 2 ₹2,500, rung 3 ₹5,000,
rung 4 ₹10,000 (the ceiling). An agent may approve an invoice up to its limit on its own;
anything above it is escalated to a human. It moves one rung at a time, never a leap.

## What an agent does with each invoice
APPROVE, REJECT or ESCALATE. Ground truth (what the right answer was) is always APPROVE or
REJECT. A **critical error** is approving an invoice that should have been rejected: money
that should not have left. Wrongly rejecting a good invoice is an error, but not a critical one.

## The numbers you will see
- **Accuracy (point)**: the share of acted decisions that matched ground truth.
- **Wilson lower bound / Wilson band**: the accuracy the evidence can actually *prove* at
  95% confidence. The ladder uses the lower bound, never the raw accuracy: 22 out of 22
  correct only proves about 85%. More decisions narrow the band, and that is what earns the
  next rung.
- **Trust score (0–100)**: four weighted parts. Wilson-bound accuracy 0.50, human agreement
  on escalations 0.25, critical-error penalty 0.15, autonomy utilisation 0.10. If a part has
  no evidence yet (human agreement needs at least 5 ruled escalations), its weight is shared
  out among the others, and the page says "weights renormalised".
- **Direction**: INCREASE, HOLD or CLAWBACK. This is what the evidence supports right now.

## When can an agent go up?
It needs all of these: at least 30 decisions, a trust score of 70 or more, no active drift, and
at least 100 decisions since its last increase (the **cooldown**). After a clawback it also needs
75 clean decisions (**clawback recovery**) before it can climb again. Even then, the increase is
only a *recommendation*. A human admin must approve it on the Approvals page.

## When does an agent go down?
A **clawback** happens automatically, with no human needed, when drift is confirmed or a
critical error happens. Taking authority away is the safe direction to fail in.

## Drift
A drop in recent accuracy against the agent's own baseline. Severity levels:
- NONE: no drop.
- WARNING: accuracy dropped more than 10 points, but the sample is too small to confirm it.
- CONFIRMED: a statistical test backs the drop up.
- CRITICAL: a critical error in the recent window. Immediate, with no statistics needed.

## Agent states
- probation: new, still building evidence.
- active: operating normally within its limit.
- restricted / suspended: taken out of autonomous service. Every decision is escalated,
  whatever the amount.

## Governance agents (the AI panel)
Four AI agents (risk, performance, compliance, audit) each review the evidence and give a
verdict: CONCUR, OBJECT or ABSTAIN. They only *recommend*. They cannot change a limit. An
objection to an INCREASE turns it into a HOLD. The backend's **hard ceiling** then cuts any
proposed limit down to what the statistics support ("clamped"), so even a hallucinating
AI cannot raise a limit on its own.

## Audit sampling
Autonomous decisions are pulled for human review at a rate that shrinks as an agent climbs:
100% at rung 0, 50% at rung 1, 25% at rung 2, 10% at rung 3, 5% at rung 4. Less oversight is
the real reward for earned trust.

## Pages in the app
Agents (list), Agent detail, Approvals, Audit Trail, Simulation, Demo Console, and the
landing page.
