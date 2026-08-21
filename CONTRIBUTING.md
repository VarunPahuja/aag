# Contributing

## Changes to `shared/`

Every file under `shared/` (`contracts.py`, `constants.py`, `enums.py`,
`reason_codes.py`) is a cross-lane treaty — every lane imports these directly,
and a breaking change to any of them breaks all four lanes at once, silently,
at import time rather than at review time.

**Any PR that touches anything under `shared/` requires approval from all four
lane owners** (backend, trust, governance, simulator/frontend) before it
merges, regardless of how small the change looks. A one-line field rename is
still a four-reviewer change — see `docs/adr/0005-shared-contracts-as-cross-lane-treaty.md`
for why this exists and for a real example of what happens when a lane drifts
from the treaty instead.

## Architectural decisions get an ADR first, not after

Any decision that changes the architecture — a new cross-lane contract, a
change to how a lane is allowed to talk to another, a change to what's
enforced where, a change to a hard rule (e.g. what `trust/` is or isn't
allowed to import) — gets an ADR in `docs/adr/` **before** the implementing
code lands, not written up afterward to justify what already merged.

Use `docs/adr/0000-template.md`. If the decision reverses an earlier one, add
a new ADR and mark the old one `Superseded by ADR-NNNN` — never rewrite an
Accepted ADR's Decision or Consequences in place. See `docs/README.md` for how
this fits with the rest of the documentation set.
