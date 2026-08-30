# ADR-0014: The Policy Engine's purity is enforced in code, not by convention

## Status

Accepted

## Context

ADR-0003 established *that* a deterministic Policy Engine is the sole
enforcement boundary — the only thing in the system that decides whether an
agent's action is permitted, independent of and downstream from the trust and
governance lanes. It did not say *how* that stays true as the module grows.
"No database, no network, no LLM" is easy to state and easy to violate by
accident six weeks later: a debugging `print(os.environ)` left in, a
convenience `datetime.now()` for a default timestamp, a "just this once"
import of a session to look something up. Each of those individually looks
harmless; together they are exactly how an enforcement boundary stops being
one, quietly, without anyone deciding it should.

Two smaller design questions came up implementing `evaluate_decision` and
`clamp_recommendation` (`backend/app/policy/`) that also needed a documented
answer rather than an implicit one: what happens when an invoice's amount
exactly equals the agent's limit, and what "no LLM anywhere near it" means in
practice for reason codes, given `shared/reason_codes.py` has none that
describe a single decision's outcome.

## Decision

**The boundary is a test, not a comment.**
`backend/tests/test_policy_import_boundary.py` parses every `.py` file under
`app/policy/` with `ast` and asserts none of them import a forbidden
top-level module — database drivers (`sqlalchemy`, `psycopg`/`psycopg2`,
`asyncpg`, `sqlite3`, ...), network clients (`requests`, `httpx`, `socket`,
...), LLM provider SDKs (`openai`, `anthropic`, `google`, ...), or `os`/`time`
(the two stdlib entry points to environment reads and wall-clock reads). This
runs on every `pytest backend/` invocation and every CI run
(`.github/workflows/ci.yml`) — a violation fails the build the same run it's
introduced, not whenever someone next reads the module carefully. Modeled on
`governance/governance/agents/base.py`'s `require_stub_mode`: that function
raises rather than silently letting a caller cross a line the architecture
depends on staying uncrossed; this test does the equivalent thing for an
import rather than a runtime call.

**The equal-to-limit boundary is inclusive, decided deliberately.**
`evaluate_decision` (`backend/app/policy/engine.py`) allows an amount exactly
equal to the agent's current limit. `docs/lanes/vp.md` phrases the ladder as
"allowed to approve up to ₹500" — an inclusive ceiling. An agent at the ₹500
rung may approve a ₹500 invoice; ₹501 escalates. This is documented in the
function's own docstring and covered by
`test_amount_exactly_at_limit_is_allowed_inclusive_boundary`
(`backend/tests/test_policy_engine.py`) precisely because the alternative
(exclusive) reading is equally plausible from the English phrasing alone, and
a boundary this consequential should never be answered by whichever way a
`<` vs. `<=` happened to get typed.

**Fail-closed is the one governing principle across every branch.** A missing
policy version, an internally inconsistent one (`rung_of(limit) != rung`, or
a limit/rung outside the valid ladder), escalates — never allows. This
extends to `PolicyDecision.within_limit` as well as `.allowed`: an engine
that cannot vouch for the policy in force does not vouch for the amount
against it either, even when the amount looks small. Verified for arbitrary
inputs by `test_never_allows_an_amount_above_the_limit` and
`test_allowed_implies_within_limit`
(`backend/tests/test_policy_properties.py`), not just the specific cases
enumerated by name.

**Policy Engine reason codes live in `backend/app/policy/reason_codes.py`,
not `shared/reason_codes.py`.** That file's own docstring scopes itself to
codes attached to a `TrustEvaluation` — rendered by the backend, styled by
the frontend, read by governance agents reasoning about autonomy. None of its
eighteen existing codes describe why one decision was allowed or escalated,
which is a different question asked by a different module at a different
point in the pipeline. `shared/` is also frozen and needs sign-off from all
four lane owners to change — adding Policy Engine codes there unilaterally,
inside a branch whose own instructions say not to touch `shared/`, would be
exactly the kind of change that needs that sign-off and didn't get it. The
new module mirrors `shared/reason_codes.py`'s own shape (append-only
constants, a `HUMAN_READABLE` map, a `describe()` helper) so promoting these
codes into `shared/` later, if the other three owners agree, is a pure move,
not a rewrite; names are prefixed `POLICY_` so that move can never collide.

## Consequences

- A future contributor cannot add a plausible-looking `import requests` (say,
  to fetch a live exchange rate for a multi-currency limit check) without the
  test suite telling them, in the same commit, exactly why not and where the
  rule comes from.
- The import-boundary test is a syntactic check, not a semantic one — it
  cannot catch a forbidden capability reached indirectly (e.g. a helper
  function passed in from outside that happens to make a network call). This
  is an accepted gap: the Policy Engine's actual public functions
  (`evaluate_decision`, `clamp_recommendation`) take only plain data
  (`Invoice`, `PolicyVersion`, two `int`s) and return only plain data, so
  there is no parameter shape through which such a capability could be
  smuggled in today. If that ever changes, the boundary needs a runtime
  check too, not just a static one.
- `backend/app/policy/reason_codes.py` and `shared/reason_codes.py` are now
  two vocabularies a reader has to know apart. This is a real cost, mitigated
  by the `POLICY_` prefix and by both modules pointing at each other's
  docstrings, but it is a cost, not a free move.
- The inclusive equal-to-limit decision is a one-rupee-wide surface a
  reviewer could reasonably disagree with. It is recorded here, with its own
  test, specifically so that disagreement has something concrete to argue
  with rather than an implicit default nobody chose on purpose.

## Alternatives considered

- **A code-review checklist item** ("Policy Engine PRs: verify no forbidden
  imports") instead of an automated test. Rejected: this is exactly the kind
  of rule a checklist enforces perfectly for the first three PRs and silently
  stops enforcing by the tenth, once review fatigue sets in — the failure
  mode ADR-0003 exists to prevent in the first place, just moved one level up
  from "the agent's own prompt" to "the reviewer's own attention."
- **Exclusive equal-to-limit boundary** (amount must be strictly less than
  the limit to be allowed). Rejected: reads against the plain-language
  framing in `docs/lanes/vp.md` ("up to ₹500"), and would mean an agent at
  its own ceiling could never actually spend up to that ceiling — a
  ₹500-limit agent effectively topping out at ₹499. Nothing in the project's
  design calls for that one-rupee (one-unit) reservation, so there is no
  reason to introduce it.
- **Reusing `RECOMMENDATION_CLAMPED` or another existing `shared/`
  code for the Policy Engine's own decisions.** Considered and rejected:
  every existing code's `HUMAN_READABLE` text (`shared/reason_codes.py`)
  describes a trust-evaluation-shaped fact ("the proposed limit exceeded the
  hard ceiling," "trust score is below the threshold"), not "this specific
  amount was compared against this specific limit." Forcing a reuse would
  make the rendered reason wrong, or require the frontend to special-case the
  same code differently depending on which module emitted it — worse than
  introducing a second, clearly-scoped vocabulary.
