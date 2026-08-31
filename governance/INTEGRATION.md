# Calling governance from the backend

For **VP**. Everything below was run on `vc/recording-fixes` on 1 Sept 2026; the numbers
are measured, not estimated. Governance owns this file — if something here is wrong,
it's my bug, come to me.

## The whole thing

```python
from governance.coordinator import recommend

recommendation = recommend(
    evaluation,                                   # a TrustEvaluation from trust_engine
    mode=None,                                    # None reads GOVERNANCE_MODE, default "stub"
    trust_evaluation_ref="trust-eval-agent01-002", # you supply this; see below
)
```

`recommend()` is the entire public surface of this lane. There is nothing else to call
and no object to construct first.

**It returns `shared.contracts.Recommendation`, and `RecommendationOut` already mirrors
it field-for-field with `from_attributes=True`.** So the wire step is:

```python
RecommendationOut.model_validate(recommendation)
```

I ran that against a real recommendation — it validates with **zero adaptation**. No
field renaming, no shim, no missing attribute:

```
model_validate OK
 agent_id     : agent-demo-01
 direction    : Direction.HOLD
 proposed     : 1000 rung 1
 has_dissent  : True
 opinions     : [('risk','CONCUR'), ('performance','OBJECT'),
                 ('compliance','CONCUR'), ('audit','CONCUR')]
 status       : RecommendationStatus.PENDING
 clamped      : False
```

## The full chain, timed

Decisions → `trust_engine.evaluate()` → `recommend()` → `RecommendationOut`:

```
stub    evaluate=0.3ms  recommend=5.2ms  serialise=0.1ms  -> HOLD 1000 dissent=True
cached  evaluate=0.2ms  recommend=7.4ms  serialise=0.0ms  -> HOLD 1000 dissent=True
```

**Cached mode does no network I/O** — it reads recorded model responses off disk. 7.4ms
is safe to call inside a request handler. Live mode is a different story and is not
open yet (due 3 Sept).

## Which mode

`GOVERNANCE_MODE` is read from the environment when you don't pass `mode` explicitly.

| Mode | What it does | Needs |
|---|---|---|
| `stub` | Hand-written reasoning, no model | nothing |
| `cached` | Replays real recorded Gemini responses | recordings on disk |
| `live` | Calls the API | **not open until 3 Sept** |

Default is `stub`, deliberately: an unset environment must never reach for a fixture
directory that may not exist, and must never be one typo away from a live API call. An
unrecognised value raises rather than falling back — a typo'd `GOVERNANCE_MODE` that
quietly ran in stub mode would look exactly like a working demo.

**For the checkpoint, `stub` is enough** and needs nothing from me. Use `cached` when you
want real model reasoning in the response.

⚠️ **One caveat on `cached` today.** Only `healthy_increase`, `thin_sample` and
`contested_increase` are fully recorded (15 of 24 calls). The Gemini free tier turns out
to be **20 requests per day**, so the rest lands over the next day or two. A cached call
for unrecorded evidence **raises `RecordingMissError`** — deliberately, see Failures
below. If you're wiring against arbitrary evidence right now, use `stub`.

## Shapes that will bite you

These cost me time; they're written down so they don't cost you any.

- **`AgentContext` has no `agent_id`.** Only `current_limit`,
  `decisions_since_last_change`, `decisions_since_clawback`, `state`.
- **`TrustEvaluation.agent_id` comes from `decisions[0].agent_id`.** An empty decision
  list yields the string `"unknown"`, not an error. `DecisionRecord` *does* have
  `agent_id`; `AgentContext` does not.
- **`AgentState` is `PROBATION` / `ACTIVE` / `RESTRICTED` / `SUSPENDED`.** There is no
  `NORMAL`.
- **`trust_evaluation_ref` is caller-supplied and optional (`str | None`).**
  `TrustEvaluation` carries no identity of its own, and you're the only component
  persisting both sides — inventing an id in this lane would produce a reference
  pointing at nothing. Your fixtures already use the right shape
  (`trust-eval-agent01-002`), so this needs no change from either of us.

## What governance will never do to you

Guaranteed by this lane, enforced in code, not just documented:

- **`status` is always `PENDING`.** Governance cannot approve its own recommendation;
  an increase needs a human (ADR-0004). Nothing here can set `APPROVED`.
- **`clamped` is always `False` and `clamped_from` always `None`.** Clamping is yours.
  Governance never reports itself as clamped.
- **`proposed_limit` never exceeds `evaluation.recommended_limit`.** There's an
  `AssertionError` guarding it. Your hard ceiling should still be enforced — this lane
  just doesn't rely on being caught.
- **No writes of any kind.** No database, no policy mutation, no limit changes. Pure
  function of the evidence you hand it (ADR-0001).

Dissent only ever ratchets toward caution: an `OBJECT` downgrades a proposed INCREASE to
HOLD. Nothing can turn a HOLD into an INCREASE or soften a CLAWBACK.

## Failures

Everything raises rather than degrading quietly, which is deliberate — a governance
path that silently falls back produces a demo that looks healthy and isn't.

| Raises | Means | Fix |
|---|---|---|
| `ValueError` | unknown `GOVERNANCE_MODE` | typo in the env var |
| `RecordingMissError` | cached mode, no recording for this evidence | record it, or use `stub` |
| `RecordingStaleError` | a prompt file was edited without a version bump | my problem, not yours — tell me |
| `OpinionParseError` | a recorded response failed validation | my problem — tell me (note: `ValueError`, not `GovernanceLLMError`) |

**Catching one exception type is not enough**, and this is the sharp edge:

- `RecordingMissError` and `RecordingStaleError` inherit `GovernanceLLMError` and carry
  `retryable = False`.
- **`OpinionParseError` inherits `ValueError`, not `GovernanceLLMError`**, and has no
  `retryable` attribute. `except GovernanceLLMError` will *not* catch it.
- `ValueError` for a bad mode is a programming error and shouldn't be caught at all —
  fix the env var.

So if you want the endpoint to survive governance failures:

```python
try:
    rec = recommend(evaluation, trust_evaluation_ref=ref)
except (GovernanceLLMError, OpinionParseError):
    rec = recommend(evaluation, mode="stub", trust_evaluation_ref=ref)
```

Nothing here is worth retrying — every failure above is a repo or disk state, not a
transient one, so a retry spends time to reach the same failure.

I'd rather fix the hierarchy than have you write that tuple. Tell me if you want
`OpinionParseError` folded under `GovernanceLLMError` and I'll do it in this lane — it's
a one-line change plus a test, and it makes your handler a single `except`.

## Two things I need from you

1. **Packaging.** I verified the above with `PYTHONPATH` pointing at `governance/`.
   `governance/pyproject.toml` builds a `governance` package, but nothing installs it
   into the backend's environment today. Editable install, path entry, or something
   else — your call, it's your lane's dependency management.
2. **When you plan to wire it.** Integration checkpoint 1 is today and
   `backend/app/api/v1/recommendations.py` still serves fixtures. The shapes line up, so
   this should be a short job — but I'd rather find that out with you than assume it.

## Not built yet

- **Live mode** — due 3 Sept, with timeout and fallback-to-cached.
- **Per-vendor and time-clustered anomaly detection** in the audit agent. Needs
  `DecisionRecord` history, which `TrustEvaluation` doesn't carry. Widening that input is
  a cross-lane contract change, so it needs an ADR before any code. Flagging it because
  it's the one thing an audit-focused question at the panel will expose.
