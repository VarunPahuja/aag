# TrustIssues Pre-Merge Audit

Audited: 2026-08-21. Read-only audit — nothing checked out, nothing fixed. All findings below are as of these commits:

- `main` / `origin/main` — `c126543`
- `origin/uk/trust` — `70b3b96`
- `origin/uk/shared-trust-contracts` — `444fdc0`

---

## 1. Repo Map

| Branch | Last commit SHA | Author | Date | Ahead of main | Behind main |
|---|---|---|---|---|---|
| `main` / `origin/main` | `c126543` | Varun | 2026-08-17 23:56 | 0 | 0 |
| `vp/backend` (local + origin) | `c126543` | Varun | 2026-08-17 23:56 | 0 | 0 |
| `vc/governance` (local + origin) | `c126543` | Varun | 2026-08-17 23:56 | 0 | 0 |
| `ad/simulator-frontend` (local + origin) | `c126543` | Varun | 2026-08-17 23:56 | 0 | 0 |
| `uk/trust` (**local**) | `c126543` | Varun | 2026-08-17 23:56 | 0 | 0 |
| `origin/uk/trust` | `70b3b96` | UtkarshSahgal | 2026-08-20 15:57 | 3 | 0 |
| `origin/uk/shared-trust-contracts` | `444fdc0` | UtkarshSahgal | 2026-08-19 17:02 | 1 | 0 |

**Zero work beyond the initial commit:** `vp/backend`, `vc/governance`, `ad/simulator-frontend` (local and origin, all identical to `main`), and the **local** `uk/trust` (which is 3 commits stale relative to its own origin — whoever is running this audit locally has not fetched Utkarsh's pushes). Every file on `main` itself — `Makefile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, and originally `shared/*.py` — is a 0-byte placeholder. The initial commit created a directory skeleton, not code.

**The only two branches with real content** are `origin/uk/trust` (3 commits, trust engine) and `origin/uk/shared-trust-contracts` (1 commit, populated `shared/`). Critically:

```
git merge-base origin/uk/trust origin/uk/shared-trust-contracts
→ c1265431e8d504376d6bd41c26988074f04537b9  (= main, the empty-scaffold commit)
```

Neither branch is an ancestor of the other — they diverged independently from `main`. `uk/trust`'s first commit (`f606d6a`, 2026-08-19 17:03:58) was authored **two minutes after** `uk/shared-trust-contracts` (`444fdc0`, 2026-08-19 17:02:09) but was branched from `main`, not from the contracts branch. This looks like Utkarsh pushed the shared contracts, then accidentally started the trust-engine branch from the wrong base instead of on top of it. The practical effect, confirmed in Section 3/5 below: **`uk/trust`'s copy of `shared/contracts.py` is still the empty placeholder**, not the file he himself wrote a commit earlier.

---

## 2. Shared Contracts

Content only exists on `origin/uk/shared-trust-contracts`. On `main` and on `origin/uk/trust`, all four files under `shared/` are 0 bytes.

### `shared/enums.py` (41 lines)

| Enum | Values |
|---|---|
| `Action(str, Enum)` | `APPROVE`, `REJECT`, `ESCALATE` |
| `AgentState(str, Enum)` | `PROBATION="probation"`, `ACTIVE="active"`, `RESTRICTED="restricted"`, `SUSPENDED="suspended"` |
| `DriftSeverity(str, Enum)` | `NONE`, `WARNING`, `CONFIRMED`, `CRITICAL` |
| `Direction(str, Enum)` | `INCREASE`, `HOLD`, `CLAWBACK` |

Note the casing split: `Action`, `DriftSeverity`, `Direction` use upper-case string values; `AgentState` uses lower-case. Anything that serializes these to JSON for the frontend (`ad/simulator-frontend`) or compares them as raw strings will get inconsistent casing across enums with no documented reason for the difference. Flag for four-way agreement.

### `shared/constants.py` (47 lines)

| Name | Type | Value |
|---|---|---|
| `SCHEMA_VERSION` | `str` | `"1.0"` |
| `CURRENCY` | `str` | `"INR"` |
| `AUTONOMY_LADDER` | `tuple[int, ...]` | `(500, 1000, 2500, 5000, 10000)` |
| `AUTONOMY_FLOOR` | `int` | `500` |
| `MAX_RUNG` | `int` | `4` |
| `TRUST_SCORE_MIN` / `MAX` | `float` | `0.0` / `100.0` |
| `CRITICAL_ERROR_DEFINITION` | `str` | prose definition |
| `rung_of(limit: int) -> int` | function | rupee amount → rung index |
| `limit_of(rung: int) -> int` | function | rung index → rupee amount, clamped |

Correctly scoped: only cross-lane values live here; the docstring explicitly says trust-engine tuning knobs belong in `trust/trust_engine/constants.py` instead. Good separation of concerns, followed correctly in practice (Section 4).

### `shared/reason_codes.py` (58 lines)

15 string constants (not a Python `Enum` — plain `Final[str]` module-level names), plus a `HUMAN_READABLE: dict[str, str]` lookup and a `describe(codes: list[str]) -> str` formatter.

**Ambiguity:** because these are bare strings typed as `str`, not an `Enum` or `Literal`, nothing stops any lane from writing an arbitrary string into `TrustEvaluation.reason_codes` — a typo (`"COOLDOWN_ACTVE"`) type-checks fine and silently falls through `describe()`'s `.get(c, f"[{c}]")` fallback instead of erroring. Four implementers could reasonably assume either "any string is fine" or "must be one of these 15" — the code doesn't enforce the latter even though the docstring intends it.

Of the 15 codes, only 3 are referenced anywhere in `uk/trust`'s code (see Section 3): `NO_ACTED_DECISIONS`, `AGREEMENT_EVIDENCE_INSUFFICIENT`, `WEIGHTS_RENORMALISED`. The other 12 — everything about autonomy increases, cooldowns, and clawback — are defined but never emitted by any code that exists today, because the logic that would emit them doesn't exist (Section 3).

### `shared/contracts.py` (169 lines)

| Dataclass | Fields (type = default) |
|---|---|
| `DecisionRecord` (frozen, slots) | `decision_id: str`, `sequence: int`, `invoice_id: str`, `amount: int`, `action: Action`, `ground_truth: Action`, `agent_id: str = "agent-01"`, `decided_at: datetime\|None = None`, `recommended_action: Action\|None = None`, `human_ruling: Action\|None = None`. Plus 6 computed properties (`is_escalated`, `is_acted`, `is_correct`, `is_critical_error`, `is_noncritical_error`, `has_human_ruling`, `human_agreed`). |
| `ProportionResult` (frozen, slots) | `successes: int`, `trials: int`, `point: float\|None`, `wilson_lower: float`, `wilson_upper: float`, + `has_evidence` property |
| `ScoreComponent` (frozen, slots) | `name: str`, `value: float\|None`, `nominal_weight: float`, `effective_weight: float`, `available: bool`, + `contribution` property |
| `AgentContext` (frozen, slots) | `current_limit: int = AUTONOMY_FLOOR`, `decisions_since_last_change: int = 0`, `decisions_since_clawback: int\|None = None`, `state: AgentState = PROBATION` |
| `DriftResult` (frozen, slots) | `severity: DriftSeverity = NONE`, `detected: bool = False`, `recent_accuracy/baseline_accuracy: float\|None`, `drop_pp: float\|None`, `z_statistic: float\|None`, `p_value: float\|None`, `critical_errors_in_window: int = 0`, `recent_n/baseline_n: int = 0`, `underpowered: bool = False` |
| `TrustEvaluation` (frozen, slots) | `agent_id: str` (required), `schema_version: str = "1.0"`, `total_decisions/acted_decisions/escalated_decisions/ruled_escalations: int = 0`, `accuracy/human_agreement/utilization: ProportionResult\|None = None`, `critical_errors/noncritical_errors: int = 0`, `critical_error_rate: float = 0.0`, `critical_errors_in_recent_window: int = 0`, `trust_score: float = 0.0`, `components: tuple[ScoreComponent,...] = ()`, `weights_renormalised: bool = False`, `drift: DriftResult = DriftResult()`, `current_limit/recommended_limit/current_rung/recommended_rung: int = 0`, `direction: Direction = HOLD`, `state: AgentState = PROBATION`, `eligible_for_increase: bool = False`, `decisions_since_last_change: int = 0`, `reason_codes: tuple[str,...] = ()`, `evaluated_at: datetime\|None = None`, `config_fingerprint: str = ""` |

**Is `TrustEvaluation` defined?** Yes, on `uk/shared-trust-contracts` only — `shared/contracts.py:132-169`. It is the complete output contract: raw evidence (`ProportionResult`s, `DriftResult`) plus the autonomy recommendation (`current_limit`/`recommended_limit`/`direction`/`eligible_for_increase`/`reason_codes`).

**Is there a `Recommendation` type?** No standalone type — the recommendation is folded directly into `TrustEvaluation` (`recommended_limit`, `recommended_rung`, `direction`, `eligible_for_increase`). There is also no contract type at all for what `vc/governance`'s LangGraph/Gemini agents are meant to hand back to the backend — governance has zero code (Section 1), so this gap is currently moot, but nothing in `shared/` anticipates it.

**Autonomy-ladder representation?** `AUTONOMY_LADDER` tuple + `rung_of()`/`limit_of()` helpers in `constants.py:16-20,23-32`. Not a type, just a lookup table — reasonable given it's a fixed 5-rung scale.

**Reason codes enumerated or raw strings?** Enumerated as constants (Section above), but typed as `str` not `Enum`/`Literal`, so nothing is actually enforced at the type level. Within `uk/trust`'s own code, only the imported constants are used — no raw string literals for reason codes were found.

**Same concept, different shapes — yes, one concrete case:** `trust/trust_engine/score.py:53-58` defines a **local** `ScoreResult` dataclass (`trust_score: float`, `components: tuple`, `renormalised: bool`, `reason_codes: tuple`) that is structurally almost `TrustEvaluation`'s scoring subset, but:
- field name `renormalised` vs. `TrustEvaluation.weights_renormalised` — different name, same meaning.
- `ScoreResult` has no `agent_id`, no ladder/limit/direction/state fields, no `drift`, no `evaluated_at`.
`compute_trust_score()` returns `ScoreResult`, never `TrustEvaluation`. Nothing in the codebase converts one into the other. Two shapes for "the scoring result," and the one the contract file promises is never actually produced.

**Unconsumed / undefined fields:**
- **Consumed-but-undefined:** none found — `uk/trust`'s imports (`DecisionRecord`, `ProportionResult`, `ScoreComponent`, `DriftResult`) all match the contract fields it reads/writes.
- **Defined-but-unconsumed:** almost the entirety of `TrustEvaluation` outside the pure-evidence fields. Nothing in `uk/trust` ever constructs a `TrustEvaluation` instance at all (verified by `grep -rn "TrustEvaluation" trust/` — zero hits in `trust_engine/`, only in the untouched contract file itself). Also **`AgentContext` is never imported or referenced anywhere in `trust/`** — the type that's supposed to carry `current_limit`, `decisions_since_last_change`, `decisions_since_clawback`, `state` from the backend into the engine has no consumer. This directly corresponds to the "autonomy ladder / cooldowns" ownership item being missing (Section 3).

**Ambiguity — `eligible_for_increase` vs. `direction`:** the contract has both a boolean `eligible_for_increase` and an `Direction` enum (`INCREASE`/`HOLD`/`CLAWBACK`). Nothing documents whether these must agree (e.g., can `eligible_for_increase=True` coexist with `direction=HOLD` if a cooldown is still pending?). Four different backend implementers could read this two different ways, and since no code produces the field yet, there's no reference implementation to settle it.

**Ambiguity — `current_rung`/`current_limit` redundancy:** both a rupee amount and a rung index are stored independently with no invariant enforced (`rung_of(current_limit) == current_rung` is not checked anywhere, and the dataclass is frozen so nothing can self-correct if a caller sets them inconsistently).

**Ambiguity — `DecisionRecord.ground_truth` provenance:** `Action` enum's own docstring (`shared/enums.py:14-16`) states "ground truth is always APPROVE or REJECT, because every synthetic invoice carries a deterministic correct answer" — i.e., this field is simulator-only by design. It's unclear how (or whether) the pipeline is meant to run against real, non-synthetic invoices, where ground truth isn't known at decision time. Relevant to Section 6.

---

## 3. Utkarsh's Work (`uk/trust`)

Files added, from `git diff main origin/uk/trust --stat`:

| File | Lines | Purpose |
|---|---|---|
| `trust/pyproject.toml` | 36 | package config: name `trust`, deps `numpy>=1.26`, `scipy>=1.12`; dev deps `pytest`, `pytest-cov`, `hypothesis`, `statsmodels`, `ruff`; `pytest` rootdir config with `pythonpath = [".", ".."]` |
| `trust/trust_engine/constants.py` | 46 | lane-local tunables: Wilson z-value, score weights, evidence gates, drift thresholds, cooldowns, snapshot cadence |
| `trust/trust_engine/stats/wilson.py` | 90 | Wilson score interval + one-sided lower bound |
| `trust/trust_engine/stats/rates.py` | 106 | partitions decisions into acted/escalated/ruled; computes accuracy, utilization, human-agreement proportions; error breakdown |
| `trust/trust_engine/stats/drift.py` | 162 | recent-vs-baseline split, two-proportion z-test, critical-error short-circuit, `detect_drift()` orchestrator |
| `trust/trust_engine/score.py` | 130 | trust-score composition with weight renormalisation and critical-error penalty |
| `trust/tests/conftest.py` | 76 | deterministic `DecisionRecord` fixture builders |
| `trust/tests/test_decision_record_contract.py` | 146 | spec-as-tests for `DecisionRecord` computed properties |
| `trust/tests/test_wilson.py` | 115 | Wilson interval unit tests, cross-checked against `statsmodels` |
| `trust/tests/test_wilson_properties.py` | 99 | Hypothesis property tests for the Wilson interval |
| `trust/tests/test_rates.py` | 152 | accuracy/utilization/human-agreement partition tests |
| `trust/tests/test_drift.py` | 122 | drift detection tests |
| `trust/tests/test_score.py` | 195 | trust-score composition tests, incl. a named regression test |

**Total: ~1,475 lines** across engine + tests (roughly 470 engine, 1,000 tests — a genuinely test-heavy ratio).

### Public functions

| Function | Signature | Returns | Pure? | Docstring matches behaviour? |
|---|---|---|---|---|
| `wilson_interval` (`wilson.py:40`) | `(successes: int, trials: int, z: float = Z_95) -> tuple[float, float]` | `(lower, upper)` | Yes | Yes — documents all 3 edge cases it actually handles |
| `wilson_lower_bound` (`wilson.py:79`) | `(successes: int, trials: int, z: float = Z_95) -> float` | `float` | Yes | Yes |
| `partition` (`rates.py:43`) | `(decisions: Sequence[DecisionRecord]) -> Partition` | local `Partition` dataclass | Yes | No docstring, name is self-explanatory |
| `accuracy` (`rates.py:62`) | `(decisions, z=Z_95) -> ProportionResult` | shared `ProportionResult` | Yes | Yes |
| `utilization` (`rates.py:70`) | `(decisions, z=Z_95) -> ProportionResult` | shared `ProportionResult` | Yes | Yes |
| `human_agreement` (`rates.py:77`) | `(decisions, z=Z_95) -> ProportionResult` | shared `ProportionResult` | Yes | Yes |
| `error_breakdown` (`rates.py:101`) | `(decisions) -> ErrorBreakdown` | local dataclass | Yes | No docstring, self-explanatory |
| `split_history` (`drift.py:37`) | `(decisions, window=RECENT_WINDOW) -> tuple[list, list]` | `(baseline, recent)` | Yes | Yes |
| `two_proportion_z` (`drift.py:58`) | `(k_recent, n_recent, k_baseline, n_baseline) -> tuple[float, float]` | `(z, p_value)` | Yes | Yes |
| `critical_errors_in_window` (`drift.py:84`) | `(decisions, window=CRITICAL_ERROR_WINDOW) -> int` | `int` | Yes | Yes |
| `detect_drift` (`drift.py:93`) | `(decisions, recent_window=..., drop_threshold_pp=..., min_n=..., alpha=...) -> DriftResult` | shared `DriftResult` | Yes | Yes |
| `critical_error_penalty` (`score.py:60`) | `(critical_errors: int, acted_total: int) -> float\|None` | `float\|None` | Yes | Yes |
| `compute_trust_score` (`score.py:69`) | `(accuracy, human_agreement, utilization, critical_errors) -> ScoreResult` | **local** `ScoreResult`, not `TrustEvaluation` | Yes | Yes, but see Section 2 mismatch |

Every function is a pure function of its arguments — no I/O, no mutable module state in `trust_engine/` itself (the only mutable module state anywhere is `_seq = itertools.count()` in `tests/conftest.py:16`, a test-fixture ID counter, not engine code, and not a hard-rule violation).

### Ownership checklist

| Ownership item | Status | Evidence |
|---|---|---|
| Wilson confidence bounds | **DONE** | `wilson.py:40-90`, cross-validated against `statsmodels` in `test_wilson.py:334-343`, correct standard/boundary behaviour (Section 4) |
| Accuracy / precision / recall metrics | **PARTIAL** | `accuracy()` (`rates.py:62`) exists and is correct. No `precision`/`recall` function exists anywhere (`grep -rn "precision\|recall" trust/` → 0 hits). Whether "accuracy" alone was meant to satisfy this brief item, or whether standalone precision/recall (e.g. over the APPROVE/REJECT confusion matrix) were expected, is undocumented — a genuine four-way-interpretable gap. |
| Human agreement score | **DONE** | `human_agreement()` (`rates.py:77`), correctly scoped to ruled escalations only, tested `test_rates.py:516-537` |
| Critical error weighting | **DONE** | `critical_error_penalty()` (`score.py:60`), `CRITICAL_ERROR_WEIGHT=5.0` (`constants.py`), applied only in the score component, never inside the accuracy proportion — by design, per `score.py:20-22` docstring, and verified in `test_score.py:885-888` |
| Recent-vs-historical drift detection | **DONE** | `detect_drift()` (`drift.py:93-162`), two-stage tripwire + z-test, tested `test_drift.py:664-723` |
| Trust score calculation | **DONE**, but wrong output type | `compute_trust_score()` (`score.py:69`) — math is correct and well-tested, but returns local `ScoreResult`, not the contract's `TrustEvaluation` (Section 2) |
| Autonomy ladder | **MISSING** | Constants exist (`AUTONOMY_LADDER`, `rung_of`, `limit_of` in `shared/constants.py`), but no function in `trust/` reads a trust score + `AgentContext` and produces a rung/limit recommendation. `grep -rn "rung_of\|limit_of\|AUTONOMY_LADDER" trust/trust_engine/` → 0 hits. |
| Cooldowns | **MISSING** | `MIN_SAMPLE_FOR_INCREASE=30`, `MIN_TRUST_SCORE_FOR_INCREASE=70.0`, `COOLDOWN_BETWEEN_INCREASES=100`, `CLEAN_DECISIONS_AFTER_CLAWBACK=75` all defined at `trust/trust_engine/constants.py:27-28,43-44`, but never referenced anywhere else in the codebase (`grep -rn` for each name outside `constants.py` → 0 hits). Dead constants. |
| Tests | **DONE** (for everything actually implemented) | 6 test files, 113 collected tests, real numeric assertions, property-based tests, one cross-validation against an independent reference implementation (Section 5) |

### Hard-rule check

`grep -rniE "fastapi|sqlalchemy|psycopg|redis|celery|import requests|httpx|open\(|os\.environ|time\.time\(\)|datetime\.now\(|global " trust/` → **no genuine violations.** The only matches were false positives from the substring `redis` inside `redistribut(ed/ion)` in comments and test names. All imports in `trust_engine/` are limited to `__future__`, `math`, `dataclasses`, `typing.Final`/`Sequence`, `shared.*`, and `trust_engine.*` (full import list captured directly, Section-supporting evidence). No FastAPI, no DB/Redis/Celery, no network calls, no file I/O, no wall-clock reads, no global mutable state in engine code.

### Contract match

`ScoreResult` (`score.py:53-58`) vs. `TrustEvaluation` — **mismatch**, detailed in Section 2. No code anywhere constructs an actual `TrustEvaluation` instance. `DriftResult` and `ProportionResult` **are** used exactly as defined in the contract — those two are a clean match.

---

## 4. Correctness of the Math

### Wilson score interval (`wilson.py:40-77`)

Implemented formula, in plain notation, for successes `k`, trials `n`, z-score `z`, `p̂ = k/n`:

```
denom   = 1 + z²/n
center  = (p̂ + z²/2n) / denom
margin  = z/denom · √( p̂(1−p̂)/n + z²/4n² )
lower   = clamp01(center − margin)
upper   = clamp01(center + margin)
```

This **is** the standard Wilson score interval (the score-test inversion), not the Wald/normal-approximation interval — the code's own docstring (`wilson.py:1-31`) correctly derives it from inverting `|p̂−p|/√(p(1−p)/n) ≤ z` rather than the Wald `|p̂−p|/√(p̂(1−p̂)/n) ≤ z`, and `test_wilson.py:255-263` explicitly asserts the Wald interval collapses to zero width at `p̂=1` while this implementation does not.

- **z-value:** `Z_95 = 1.96` (`trust_engine/constants.py:14`) — the conventional rounded 95% value, not the exact `1.959963984540054`. The gap is ~4e-5, immaterial in practice. It **is configurable per call** (`z: float = Z_95` parameter on both `wilson_interval` and `wilson_lower_bound`), but there's no "confidence level" percentage parameter — a caller must already know the z-score for whatever level they want.
- **Cross-check:** `test_wilson.py:334-343` validates against `statsmodels.stats.proportion.proportion_confint(..., method="wilson")` using the exact z-value — this is a real, non-trivial correctness check, not just a smoke test.
- **`n = 0`:** returns `(0.0, 1.0)` (`wilson.py:53-54`) — maximal uncertainty, standard convention, tested `test_wilson.py:275-276`.
- **`successes = 0`:** lower bound forced to exactly `0.0` (`wilson.py:72-73`) to counter float noise (the code comments this explicitly: raw arithmetic leaves ~7e-18 instead of 0). Tested `test_wilson.py:279-282`.
- **`successes = trials` (all successes):** upper bound forced to exactly `1.0` (`wilson.py:74-75`), lower stays strictly below 1 — this is presented in the code's own docstring as "the case the whole module exists for" and is the correct, intentional behaviour that distinguishes Wilson from Wald. Tested `test_wilson.py:285-286` and property-tested `test_wilson_properties.py:388-397`.
- **`n = 1`:** not special-cased, falls through the general formula — correct, since the formula is well-defined for `n=1`; covered implicitly by the parametrized/hypothesis tests (`n` ranges include `1`).
- **Impossible counts** (`successes > trials`, negative counts): raises `ValueError` (`wilson.py:47-50`), tested `test_wilson.py:289-293` and property-tested `test_wilson_properties.py:437-444`.

No division-by-zero risk: the `n=0` branch returns before the `n` is used as a divisor.

### Drift detection (`drift.py`)

**"Recent" vs. "historical":** `split_history()` (`drift.py:37-51`) takes the **last `window` decisions by sequence number** as "recent"; everything before that is "baseline." Default `window = RECENT_WINDOW = 50`, hardcoded in `trust/trust_engine/constants.py` (lane-local, not in `shared/constants.py` — consistent with that file's documented intent). If total decisions ≤ window, baseline is empty and the function returns `([], all_decisions)` — i.e. everything is "recent," correctly signalling "no baseline to compare against" rather than crashing. `detect_drift()` handles this by returning `DriftSeverity.NONE` when either `recent_acc` or `baseline_acc` is `None` (`drift.py:118-124`), tested `test_drift.py:706-709`.

**Two-proportion z-test** (`two_proportion_z`, `drift.py:58-79`), standard pooled form for proportions `p_recent = k_r/n_r`, `p_baseline = k_b/n_b`, pooled `p̄ = (k_r+k_b)/(n_r+n_b)`:

```
variance = p̄(1−p̄)(1/n_r + 1/n_b)
z = (p_recent − p_baseline) / √variance
p_value = Φ(z)   (one-sided; only "recent is worse" is flagged as drift)
```

This is the textbook pooled two-proportion z-test. Guarded: `n_recent<=0 or n_baseline<=0` returns `(0.0, 1.0)` before dividing (`drift.py:66-67`); `variance<=0.0` (e.g. `p̄∈{0,1}`) also returns `(0.0, 1.0)` before the divide (`drift.py:74-75`) — both division-by-zero paths are closed, tested `test_drift.py:637-643`.

**Two-stage severity logic** (`detect_drift`, `drift.py:93-162`):
1. Critical-error short-circuit: any critical error in the last `CRITICAL_ERROR_WINDOW=20` acted decisions → immediate `DriftSeverity.CRITICAL`, no statistics run (`drift.py:107-115`).
2. Tripwire: `drop_pp = (baseline_acc − recent_acc) × 100 ≥ DRIFT_ACCURACY_DROP_PP=10.0` pp must fire before the z-test even runs (`drift.py:132-140`).
3. Confirmation: if `n_recent < 30 or n_baseline < 30` (`DRIFT_MIN_N_FOR_TEST`), severity stays `WARNING` regardless of the p-value (underpowered); otherwise `p_value < DRIFT_ALPHA=0.05` → `CONFIRMED`, else `WARNING` (`drift.py:142-151`).

This is a reasonable, explicitly-justified design (documented in the module docstring) and the underpowered/confirmed/warning split is tested (`test_drift.py:671-703`).

### Trust score (`score.py`)

Weights (`trust_engine/constants.py:17-20`): `WEIGHT_WILSON_LOWER=0.50`, `WEIGHT_HUMAN_AGREEMENT=0.25`, `WEIGHT_CRITICAL_PENALTY=0.15`, `WEIGHT_UTILIZATION=0.10` — sum to 1.0, verified by `test_score.py:770-772`. These are hardcoded magic numbers, but correctly located in the lane-local `trust_engine/constants.py`, not buried inline in `score.py` and not misplaced into `shared/constants.py`.

`critical_error_penalty(critical_errors, acted_total)`: `1.0 − CRITICAL_ERROR_WEIGHT × (critical_errors/acted_total)`, clamped to `≥0`, `None` if `acted_total==0` (avoids division by zero, `score.py:63-64`). `CRITICAL_ERROR_WEIGHT=5.0` means the penalty hits zero at a 20% critical-error rate — tested exactly at that boundary (`test_score.py:858-860`).

Renormalisation: accuracy and utilization are **never** dropped once any decision exists (abstaining scores 0 rather than being excluded) — this is explicitly a fixed regression, documented in `score.py:14-18` and guarded by a named test (`test_score.py:834-845`, "an earlier version... scored 'do nothing' at 68.8/100"). Human agreement and critical-penalty **are** droppable when their evidence gate isn't met (`MIN_RULED_ESCALATIONS_FOR_AGREEMENT=5`, `score.py:27,84-85`), with weight redistributed proportionally to the remaining components' nominal weights (`score.py:96-104`), tested for proportionality (`test_score.py:808-812`) and for summing back to 1.0 (`test_score.py:796-799`).

**Autonomy ladder / cooldowns:** the relevant constants (`MIN_SAMPLE_FOR_INCREASE=30`, `MIN_TRUST_SCORE_FOR_INCREASE=70.0`, `COOLDOWN_BETWEEN_INCREASES=100`, `CLEAN_DECISIONS_AFTER_CLAWBACK=75`) are hardcoded but correctly placed in `trust_engine/constants.py` — **however there is no formula to evaluate**, because nothing in the codebase reads them (Section 3). There is no math to check here because the math doesn't exist yet.

---

## 5. Tests

**As committed on `uk/trust` (`70b3b96`), against `main`'s empty `shared/contracts.py`:** 0 tests collect. Verbatim:

```
ImportError while loading conftest '...\trust\tests\conftest.py'.
tests\conftest.py:12: in <module>
    from shared.contracts import DecisionRecord
E   ImportError: cannot import name 'DecisionRecord' from 'shared.contracts' (...\shared\contracts.py)
```

This is not an environment artifact — it reproduces because `shared/contracts.py` genuinely is 0 bytes on this branch (Section 1/2). Anyone pulling `uk/trust` today and running `pytest` gets this exact failure before a single test runs.

**With `shared/` overlaid from `origin/uk/shared-trust-contracts`** (i.e., simulating the merge that should have happened), run via `pytest -v --tb=short` in a clean venv (`pytest==9.1.1`, `hypothesis==6.165.10`, no `numpy`/`scipy`/`statsmodels` installed):

```
collected 113 items

tests\test_decision_record_contract.py ...........                       [  9%]
tests\test_drift.py ................                                     [ 23%]
tests\test_rates.py .................                                    [ 38%]
tests\test_score.py ....................                                 [ 56%]
tests\test_wilson.py ........................................s           [ 92%]
tests\test_wilson_properties.py ........                                 [100%]

======================= 112 passed, 1 skipped in 2.32s ========================
```

The 1 skip is `test_matches_statsmodels_reference_implementation` (`test_wilson.py:334`), which uses `pytest.importorskip("statsmodels...")` — it skipped only because `statsmodels` (a heavy, transitively-`numpy`/`scipy`/`pandas`-dependent package) wasn't installed in this audit environment, not because of a code defect.

**Note on dependencies:** `trust/pyproject.toml` declares `numpy>=1.26` and `scipy>=1.12` as hard runtime dependencies, but `grep -rn "^import numpy\|^import scipy\|from numpy\|from scipy" trust/trust_engine/` returns **zero hits** — the engine code uses only `math` from the standard library. These two packages are pulled in for no functional reason (only `statsmodels`, a *dev*-only cross-check dependency, would need them, and even that's `importorskip`-guarded). This cost real time in this audit (a `scipy` wheel download stalled and had to be worked around) and will cost the same in CI. Worth trimming.

**Coverage assessment, honestly:** every component that exists has real tests with concrete numeric expectations (e.g. `wilson_lower_bound(10,10) == pytest.approx(0.7225, abs=1e-4)`, exact boundary equalities, hypothesis property tests, and a genuine cross-validation against an independent library) — this is not "assert it doesn't raise" testing, it's real. The gap is exactly the gap identified in Section 3: **autonomy ladder, cooldowns, clawback, and any `TrustEvaluation`-producing entry point have zero tests, because they have zero implementation.** `test_decision_record_contract.py` also tests something no one else asked for but is genuinely valuable — it documents, as executable tests, the exact simulator-side landmines (missing `recommended_action`/`human_ruling`) that `ad/simulator-frontend` needs to avoid, per its own file header aimed at "Adhya."

---

## 6. Integration Readiness

**There is no single entry point.** No function anywhere in `trust/` takes `(decisions, agent_context)` and returns a `TrustEvaluation`. A backend integrator today would have to hand-assemble the pipeline themselves:

```python
from trust_engine.stats.rates import accuracy, utilization, human_agreement, error_breakdown
from trust_engine.stats.drift import detect_drift
from trust_engine.score import compute_trust_score

acc = accuracy(decisions)                       # ProportionResult
util = utilization(decisions)                   # ProportionResult
agree = human_agreement(decisions)               # ProportionResult
errors = error_breakdown(decisions)              # local ErrorBreakdown
drift = detect_drift(decisions)                  # DriftResult (matches shared contract)
score = compute_trust_score(acc, agree, util, errors.critical)   # local ScoreResult, NOT TrustEvaluation
```

What the backend must then supply that nothing today produces:
- **The `AgentContext`** (current limit, decisions since last change/clawback, state) — defined in `shared/contracts.py` for exactly this purpose, but no `trust/` function accepts it, so the backend gets no help applying cooldowns or clawback recovery even if it wanted to call into the engine for that.
- **The autonomy-ladder decision itself** (rung/limit recommendation, `Direction`, `eligible_for_increase`, the 12 unused reason codes) — this was `uk/trust`'s ownership item and is entirely unimplemented (Section 3); the backend would end up writing this logic itself, which defeats the point of a separate trust lane.
- **A `TrustEvaluation` instance** — the backend would have to hand-map `ScoreResult` + `DriftResult` + the four `ProportionResult`s into `TrustEvaluation`'s ~25 fields itself, guessing at the semantics flagged as ambiguous in Section 2 (`eligible_for_increase` vs `direction`, `current_rung` vs `current_limit` consistency).
- **`DecisionRecord.ground_truth`** — per Section 2, this is documented as simulator-only. `vp/backend` has zero code today, and it's undefined how (or whether) ground truth would ever be known for a real, non-synthetic invoice at evaluation time. This needs a design decision before "integration" means anything beyond replaying simulator output.
- **`recommended_action`/`human_ruling`** for escalated decisions — these are meant to come from a human-review workflow, presumably surfaced through `vc/governance`, which also has zero code. Without them, `human_agreement()` can never have evidence in any environment except the simulator's synthetic fixtures.

Given `vp/backend` is byte-for-byte identical to `main` (Section 1), "integration readiness" is currently a moot question on the backend side regardless of trust-engine quality — there is no code on either end of the wire yet.

---

## 7. Merge Verdict

**`uk/trust`: MERGE AFTER LISTED FIXES.**

The math that exists is correct, well-documented, and rigorously tested (Sections 4-5) — this is not a "redo the statistics" verdict. But the branch cannot merge as committed (it doesn't even import), and what's missing is exactly the part of the ownership brief that makes this an "earned autonomy engine" rather than a statistics library: the ladder, the cooldowns, the clawback, and the contract type the rest of the team is meant to consume.

1. **Merge `origin/uk/shared-trust-contracts` into `uk/trust`** (or rebase `uk/trust` onto it) so `shared/contracts.py`, `constants.py`, `enums.py`, `reason_codes.py` are populated. This blocks everyone, not just this branch — every other lane will hit the identical `ImportError` the moment it tries to import `shared.contracts`. Single commit, do this first.
2. **Add an orchestrator function** (e.g. `evaluate(decisions: Sequence[DecisionRecord], context: AgentContext) -> TrustEvaluation`) that wires together `accuracy`/`utilization`/`human_agreement`/`error_breakdown`/`detect_drift`/`compute_trust_score` and returns the actual shared `TrustEvaluation` type. This is the integration entry point the backend needs and currently doesn't have.
3. **Implement the autonomy-ladder/cooldown/clawback decision logic** using the constants that already exist but are unused (`MIN_SAMPLE_FOR_INCREASE`, `MIN_TRUST_SCORE_FOR_INCREASE`, `COOLDOWN_BETWEEN_INCREASES`, `CLEAN_DECISIONS_AFTER_CLAWBACK`), and have it emit the 12 currently-dead reason codes (`INSUFFICIENT_SAMPLE`, `COOLDOWN_ACTIVE`, `TRUST_BELOW_THRESHOLD`, `AT_MAX_RUNG`, `DRIFT_ACTIVE`, `CLAWBACK_RECOVERY_PENDING`, `EVIDENCE_SUFFICIENT`, `NO_DRIFT_DETECTED`, `NO_RECENT_CRITICAL_ERRORS`, `COOLDOWN_SATISFIED`, `CLAWBACK_DRIFT`, `CLAWBACK_CRITICAL_ERROR`).
4. **Retire the local `ScoreResult`** in favor of `compute_trust_score` feeding directly into the orchestrator from #2 — right now it's a second, incompatible shape for "the trust score."
5. **Add tests for #2 and #3** — currently the largest chunk of the ownership brief (ladder, cooldowns, clawback) has zero test coverage because it has zero implementation.
6. **Resolve the precision/recall ambiguity** — document explicitly whether `accuracy()` alone satisfies "accuracy/precision/recall metrics," or add the missing functions.
7. **Drop the unused `numpy`/`scipy` dependencies** from `trust/pyproject.toml` (nothing imports them) to stop paying their install cost in CI.
8. **Document the `ground_truth` provenance question** (Section 2/6) — at minimum a comment in `shared/contracts.py` clarifying that `DecisionRecord.ground_truth` is simulator-sourced today and what (if anything) is expected to supply it once real invoices are involved.

Items 1-4 block other lanes and should land before anyone else builds against this package. Items 5-8 are quality/hygiene and can follow in the same sprint.

---

## Summary

- `shared/` contracts (types, enums, constants, reason codes) exist and are well-designed, but only on an **unmerged sibling branch** — `uk/trust` still points at the empty placeholder version.
- As committed, `uk/trust` **cannot even be imported**: `pytest` collects 0 tests, `ImportError` on the first line of `conftest.py`.
- With the contracts merged in (not yet done), the actual math is **correct and well-tested**: 112 passed / 1 skipped, Wilson bounds cross-validated against `statsmodels`, all boundary/zero-division cases handled.
- **Half the ownership brief is missing outright**, not buggy: autonomy ladder, cooldowns, and clawback are constants with no implementing logic; 12 of 15 reason codes are never emitted.
- There is **no function that produces the `TrustEvaluation` contract type** — `compute_trust_score` returns a different, local shape instead.
- `AgentContext` — the type meant to carry the backend's state into the engine — is imported nowhere.
- `vp/backend`, `vc/governance`, `ad/simulator-frontend` are all byte-identical to `main`: zero code exists to call any of this yet.
- Precision/recall, explicitly named in the ownership brief, don't exist as functions; only `accuracy()` does.
- `numpy`/`scipy` are declared dependencies the engine never actually imports — pure install-time cost.
- **Biggest risk to the 12 September deadline: the trust engine's pure-math core is done, but the "earned autonomy" decision logic — the actual product concept — hasn't been started, and nothing exists yet to plug the engine into a backend that also doesn't exist.** The contracts-branch merge (fix #1) is a 5-minute git operation; the missing ladder/cooldown/orchestrator logic (fixes #2-3) is real, unstarted work, and every other lane is blocked from writing real integration code until it lands.
