# Audit Trail

Route: `/audit`

## What this page is for
The permanent, tamper-evident record of everything that happened: every decision, every
recommendation and human ruling, every autonomy change. Each entry is hash-linked to the one
before it, so any edit to history breaks the chain and shows up here.

## What you see
- **Hash chain indicator (top right)**:
  - *Hash Chain: Verified*, with its scope and the entry count: the backend recomputed the
    chain and it is intact.
  - *Hash Chain: BROKEN*: an entry was altered. Treat this as tampering and investigate.
  - The page never checks the chain itself. It shows the backend's result.
- **Table**, 25 entries per page, refreshed every 10 seconds, with columns ID, Event, Actor
  (and actor type), Entity (type and id), Hash (shortened) and Timestamp.
- Event types include Decision · Recorded, Policy Version · Created, Recommendation ·
  Generated / Approved / Rejected, and Audit Sample · Reviewed.

## What you can do here
- Click any row to open **Record inspection**: full entry id, event type, actor, entity,
  exact timestamp, the **previous hash** and **hash** (the link in the chain), and the
  entry's full JSON payload.
- Use PREVIOUS / NEXT at the bottom to page through history.

## Common questions
- *What does the hash chain prove?* Each entry's hash includes the previous entry's hash. If
  any past entry were changed, every hash after it would stop matching and the indicator
  would show BROKEN.
- *Who is the actor?* The user or system component that caused the event. The actor type
  says which kind.
- *Can entries be deleted or edited here?* No. The page is read-only, and the log is
  append-only by design.
