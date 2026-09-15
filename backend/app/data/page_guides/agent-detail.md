# Agent detail

Route: `/agents/{id}`

## What this page is for
Everything about one agent: where it stands, the statistical evidence behind that, how its
autonomy has changed over time, and its recent decisions. When the assistant is opened here,
it also receives this agent's own live evidence (and no other agent's).

## What you see, top to bottom
- **Header**: name, id, STATE badge, RUNG tag, a DRIFT badge if drift is not NONE, and
  CURRENT AUTONOMY (the spending limit). Next to it may be the evidence's direction
  (INCREASE / CLAWBACK), **ELIGIBLE FOR INCREASE**, or **AUTONOMY CLAWED BACK** if the agent
  has ever been moved down a rung.
- **Metric strip**: TRUST SCORE (0–100), TOTAL DECISIONS, ACCURACY (raw point estimate),
  WILSON BAND (the proven lower–upper range of accuracy), SAMPLING RATE (the share of
  autonomous decisions pulled for human review at this rung), and DIRECTION.
- **How autonomy changed**: a timeline chart of the limit over time. The shaded band narrows
  as evidence builds up, and that narrowing unlocks higher rungs.
- **Why autonomy changed**: the current direction explained in plain language from reason
  codes. It shows current and recommended limit, ELIGIBLE (yes/no), SINCE LAST CHANGE
  (decisions since the last limit change) and the raw reason-code tags.
- **Reliability position**: a gauge placing raw accuracy and the Wilson lower bound against
  the thresholds. Below it are the **score components** with their effective weights (w=…),
  and a warning if the weights were renormalised. If drift is detected there is a
  **DRIFT DETECTED** box comparing recent against baseline accuracy.
- **Autonomy ladder** and **Review burden by rung**: the sampling rate at each rung
  (100% / 50% / 25% / 10% / 5%), with this agent's rung highlighted.
- **Governance event history**: every policy change, oldest first: the initial policy,
  promotions (green) and automatic clawbacks (red), each with its reason.
- **Recent decisions**: up to 20 of the latest decisions, showing action (APPROVE / REJECT /
  ESCALATE), invoice id, amount and time.

## What you can do here
This page is read-only. To change anything:
- Approve or reject a proposed increase on the **Approvals** page (admin only).
- Build fresh evidence for an agent on the **Simulation** page.

## Common questions
- *Why is the agent not eligible for an increase?* Read the reason codes in "Why autonomy
  changed". An increase needs 30+ decisions, a trust score of 70+, no active drift, 100 decisions
  since the last increase, and 75 clean decisions after any clawback.
- *Why is accuracy high but the agent not promoted?* The ladder reads the Wilson lower bound,
  not the raw accuracy. A small sample proves less.
- *Why was a specific invoice approved?* No per-invoice reasoning is recorded. Only the
  action, the ground truth, whether it was within the limit, and the policy version.
- *What does sampling rate mean?* The fraction of this agent's autonomous decisions that a
  human reviews afterwards. It shrinks as the agent climbs.
