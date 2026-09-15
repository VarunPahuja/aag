# Approvals

Route: `/approvals` (the page title is "Recommendations")

## What this page is for
The human review queue. Every recommendation the governance panel produces lands here, and
an autonomy **increase** only takes effect when a human approves it. Clawbacks never wait
here: they apply automatically.

## What you see
- **PENDING REVIEW counter**: how many recommendations are waiting.
- **Filter tabs**: PENDING, APPROVED, REJECTED, ALL.
- **One row per recommendation**:
  - direction (↑ INCREASE, — HOLD, ↓ CLAWBACK), agent id, proposed limit and proposed rung
  - **CLAMPED from ₹…**: the backend's hard ceiling cut the proposal down to what the
    statistics support
  - **⚠ DISSENT**: at least one governance agent objected. A pending row with dissent gets a
    red left border.
  - how long ago it was generated, and its status (PENDING, APPROVED, REJECTED or
    SUPERSEDED; superseded means newer evidence replaced it before anyone acted)
  - the rationale
- **Governance agent opinions** (expand the row): one card each for the risk, performance,
  compliance and audit agents, showing their verdict (CONCUR / OBJECT / ABSTAIN), reasoning,
  concerns and confidence.

## What you can do here
1. Expand a row and read the four opinions, especially any OBJECT.
2. Type a reason in the **Reason (mandatory)** box. The buttons stay disabled until you do.
3. Click **APPROVE** or **REJECT**.

Only an **admin** can approve or reject. Other roles see "Permission denied". If someone
else resolved the recommendation first, you see "already been resolved". Approving an increase
creates a new policy version and moves the agent up a rung.

## Common questions
- *Why is there nothing to approve for a clawback?* Taking authority away never needs a human
  (ADR-0004). It already happened.
- *What does "clamped" mean?* The panel proposed more than the evidence supports, so
  deterministic backend code reduced it. The AI can never raise a limit past the evidence.
- *Should I approve if there is dissent?* The assistant cannot decide for you. Read the
  objecting agent's concerns. An objection to an increase usually means the panel already
  softened it to a HOLD.
- *Can the assistant approve this for me?* No. The assistant is read-only. Use the APPROVE /
  REJECT buttons.
