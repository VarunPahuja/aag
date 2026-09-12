"""Executing a simulation run: generate invoices, run a scripted agent over
them, and submit every resulting decision through the real ingest path
(`app.api.v1.decisions._create_decision` — never a shortcut into the
database) — recording progress and a final summary (or a recorded failure)
on the `simulation_runs` row as it goes.

Why this does not import `simulator/`
--------------------------------------
`app/schemas/simulation.py` already establishes the rule for this exact pair
of lanes: "`SimulationPhase` mirrors `simulator.simulator.models.
SimulationPhase` by value, not by import... the simulator submits to this
API, this API does not reach into the simulator." Two more reasons specific
to this endpoint, found while reading `simulator/` before writing this file:

1. As of this writing, `simulator/simulator/models.py`'s `Invoice.invoice_id`
   defaults to a bare, unseeded `uuid4()` — a different id on every call,
   seed or no seed. Importing that model as-is would make this endpoint
   non-deterministic by construction, which is a hard requirement here
   ("same seed, same run, every time"). Fixing that bug is the simulator
   lane's own reproducibility work in flight elsewhere
   (docs/audits/2026-09-06-audit.md, PR #30 on `uk/simulator-finalise`,
   unmerged as of this branch) — this branch doesn't reach into another
   lane's open work to patch it, it just doesn't depend on the unfixed
   version.
2. `simulator/`'s CLI and runner pull in `typer`, `rich`, and their own
   `httpx.Client` — none of which the backend's runtime otherwise needs.

What this module *does* reuse from another lane is
`trust_engine.stats.wilson.wilson_lower_bound` for the run summary — not a
new coupling: `app/services/trust.py` already imports
`trust_engine.evaluate` for exactly this reason (a pure statistics library
the backend is meant to call, unlike `simulator/`, which is meant to call
the backend).
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from shared.enums import Action
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from trust_engine.stats.wilson import wilson_lower_bound

from app.models import Agent, Decision
from app.models.audit_log import append_entry
from app.models.simulation_runs import SimulationRun
from app.schemas.decision import DecisionCreate
from app.schemas.simulation import RunStatus, SimulationPhase

# Per-decision probabilities, deliberately independent of each other rather
# than derived from one combined "error rate" — degraded phase needs a
# meaningfully elevated *critical*-error rate specifically (an APPROVE whose
# ground truth is REJECT — shared.constants.CRITICAL_ERROR_DEFINITION) for
# drift detection and clawback to actually fire within a realistic window
# (trust/trust_engine/constants.py's CRITICAL_ERROR_WINDOW=20 acted
# decisions); good/recovery phases need that rate low while still allowing
# some ordinary (non-critical) mistakes.
_PHASE_PARAMS: dict[SimulationPhase, dict[str, float]] = {
    SimulationPhase.GOOD: {
        "p_ground_truth_reject": 0.20,
        "p_critical_error": 0.02,
        "p_noncritical_error": 0.06,
    },
    # Retuned so the phase can actually show what it is named for. At
    # p_ground_truth_reject 0.20 / p_critical_error 0.12 the expected accuracy
    # was ~86% — a few points below `good`, indistinguishable on a dashboard —
    # and a critical error landed on only 2.4% of decisions, so the chance of
    # one falling inside CRITICAL_ERROR_WINDOW (20 acted decisions) was under
    # half. A "degraded" run therefore usually finished with no drift, no
    # clawback, and a trust score that had barely moved.
    #
    # More REJECT-worthy invoices, and a much higher chance of approving one,
    # gives ~65% expected accuracy and puts a critical error in the recent
    # window with probability ~0.97. This is what the comment above always
    # intended; the numbers just did not reach it.
    SimulationPhase.DEGRADED: {
        "p_ground_truth_reject": 0.35,
        "p_critical_error": 0.45,
        "p_noncritical_error": 0.30,
    },
    SimulationPhase.RECOVERY: {
        "p_ground_truth_reject": 0.20,
        "p_critical_error": 0.03,
        "p_noncritical_error": 0.08,
    },
}


class PlannedDecision:
    """One invoice's amount, ground truth, and the scripted agent's action —
    everything `DecisionCreate` needs except `agent_id`/`reason`, which the
    caller already knows."""

    __slots__ = ("action", "amount", "ground_truth", "invoice_id", "recommended_action")

    def __init__(
        self,
        invoice_id: str,
        amount: int,
        action: Action,
        ground_truth: Action,
        recommended_action: Action | None = None,
    ) -> None:
        self.invoice_id = invoice_id
        self.amount = amount
        self.action = action
        self.ground_truth = ground_truth
        # Only set when `action` is ESCALATE: the APPROVE/REJECT the agent
        # would have chosen had it been allowed to act alone. Half of the
        # human-agreement evidence; the human's ruling is the other half.
        self.recommended_action = recommended_action


def generate_decision_plan(
    *,
    agent_id: str,
    phase: SimulationPhase,
    seed: int,
    count: int,
    current_limit: int,
) -> list[PlannedDecision]:
    """Pure and deterministic: the same (agent_id, phase, seed, count,
    current_limit) always produces the same list, in the same order —
    nothing here reads a clock, mints a `uuid4()`, or otherwise draws on
    anything but the seeded `random.Random` stream below.

    Seeded with a composite *string*, not the bare `seed` int, so two
    different agents (or the same agent run twice under different phases)
    given the same numeric seed don't produce the same invoices as each
    other — only a genuine repeat of the same (agent, phase, seed) does.

    `invoice_id`s are deterministic and namespaced by **every input that
    decides an invoice's content** — (agent_id, phase, seed, current_limit,
    index). A repeat run with all five identical reuses the same invoice ids
    on purpose, matching `_create_decision`'s own "an invoice is a fact
    recorded once" rule rather than fighting it: those really are the same
    synthetic invoices being reprocessed.

    `current_limit` has to be in the id, and leaving it out was a real bug.
    Amounts are drawn from `randint(10, max(current_limit * 2, 1000))`, so
    the limit decides both the amount and — through the shared `rng` stream —
    every ground truth after it. An id that omitted it therefore promised
    "same id, same invoice" and broke that promise the moment the agent's
    limit moved, which is the one thing this whole system exists to do.
    `_create_decision` never overwrites an existing invoice's `amount` or
    `ground_truth_action`, so a re-run at a new limit wrote decisions whose
    recorded ground truth belonged to a *different* invoice: accuracy was
    then scored against the wrong answer key. Observed live on agent-01 —
    after two clawbacks took it from INR 2,500 to the floor, all 20 invoices
    in its critical-error window still held amounts up to INR 4,859 drawn at
    the old limit, and a phantom critical error in there pinned drift to
    CRITICAL so no good run could ever clear it.
    """
    rng = random.Random(f"{agent_id}:{phase.value}:{seed}")
    params = _PHASE_PARAMS[phase]
    lo = 10
    hi = max(current_limit * 2, 1000)

    plan: list[PlannedDecision] = []
    for i in range(count):
        invoice_id = f"sim-{agent_id}-{phase.value}-{seed}-L{current_limit}-{i:05d}"
        amount = rng.randint(lo, hi)

        if rng.random() < params["p_ground_truth_reject"]:
            ground_truth = Action.REJECT
            # The only way to be "wrong" about a REJECT-worthy invoice with
            # just two possible actions is to APPROVE it — the critical
            # error by definition.
            action = Action.APPROVE if rng.random() < params["p_critical_error"] else Action.REJECT
        else:
            ground_truth = Action.APPROVE
            action = Action.REJECT if rng.random() < params["p_noncritical_error"] else Action.APPROVE

        if amount > current_limit:
            # The agent may not act alone on this, so it defers to a human.
            # Previously the plan produced APPROVE/REJECT for every invoice
            # regardless of amount, so a simulated agent never escalated — and
            # with no escalations there were no human rulings, which left the
            # trust score's fourth component (`human_agreement`) permanently
            # without evidence (AGREEMENT_EVIDENCE_INSUFFICIENT and
            # WEIGHTS_RENORMALISED on every single evaluation) and made the
            # governance audit agent OBJECT for ever. One objection downgrades
            # an INCREASE to a HOLD (governance/coordinator.py::_aggregate), so
            # no simulation run could ever produce an approval request, no
            # matter how well the agent performed.
            plan.append(
                PlannedDecision(
                    invoice_id, amount, Action.ESCALATE, ground_truth, action
                )
            )
        else:
            plan.append(PlannedDecision(invoice_id, amount, action, ground_truth))

    return plan


def execute_simulation_run(run_id: str, engine: Engine) -> None:
    """The `BackgroundTasks` entry point. Runs after the `POST` response has
    already been sent, on its own thread (Starlette runs a synchronous
    background callable via `run_in_threadpool`) and its own `Session`s —
    never the request's, which is already closed by the time this executes.

    `engine` is the exact bind the triggering request's own `db: DbSessionDep`
    was using (`app.api.v1.simulation.start_simulation_run` passes
    `db.get_bind()`), not `app.deps`'s process-wide default engine. That
    default is built lazily and cached at module-global scope on first use,
    and every test in this suite replaces `get_session` via
    `app.dependency_overrides` to point at a throwaway per-test database —
    bypassing that override by reaching for the global default here would
    silently point every simulation run at the wrong database in tests (and
    at a stale one if `DATABASE_URL` ever changed between processes sharing
    one import of this module). Taking the engine as a parameter avoids that
    entirely: this function always talks to whatever database the request
    that started it was actually using.

    Every decision is submitted as its own transaction, through
    `app.api.v1.decisions._create_decision` — the exact function
    `POST /api/v1/decisions` itself calls — so, to the rest of the system, a
    simulation run looks identical to a real client submitting one decision
    at a time. `_create_decision` already serializes correctly per agent
    (the agent-row lock from PR #31's Race 1 fix); nothing here adds any
    locking or retry logic of its own, and nothing here needs to: each
    decision waits for the previous one's transaction to fully commit before
    the next one starts, so there is no concurrent access to serialize in
    the first place.

    A failure on any one decision stops the run there — the run is marked
    FAILED with however many decisions actually succeeded and why, rather
    than either silently reporting a short "completed" count with no
    explanation, or continuing to submit decisions against whatever broke.
    """
    from app.api.v1.decisions import _create_decision  # deferred: see module docstring's read order

    plan_session = Session(engine)
    try:
        run = plan_session.get(SimulationRun, run_id)
        if run is None:
            return  # the row is committed before this task is ever scheduled; not reachable in practice
        agent = plan_session.get(Agent, run.agent_id)
        phase = run.phase
        seed = run.seed
        invoice_count = run.invoice_count
        agent_id = run.agent_id
        current_limit = agent.current_limit
    finally:
        plan_session.close()

    plan = generate_decision_plan(
        agent_id=agent_id,
        phase=phase,
        seed=seed,
        count=invoice_count,
        current_limit=current_limit,
    )

    submitted = 0
    acted = 0
    correct = 0
    escalated_ids: list[str] = []
    failure: str | None = None

    for planned in plan:
        decision_session = Session(engine)
        try:
            body = DecisionCreate(
                invoice_id=planned.invoice_id,
                amount=planned.amount,
                action=planned.action,
                ground_truth=planned.ground_truth,
                agent_id=agent_id,
                recommended_action=planned.recommended_action,
                reason=f"simulation run {run_id} ({phase.value}, seed {seed})",
            )
            decision = _create_decision(decision_session, body)
            if planned.action is Action.ESCALATE:
                escalated_ids.append(decision.id)
            decision_session.commit()
        except Exception as exc:  # noqa: BLE001 — recorded on the run, not swallowed
            decision_session.rollback()
            failure = f"{type(exc).__name__}: {exc}"
            decision_session.close()
            break
        else:
            decision_session.close()

        submitted += 1
        if planned.action is not Action.ESCALATE:
            # Accuracy is over decisions the agent actually made. An escalation
            # is a deferral, not a right or wrong answer — the same rule
            # `trust_engine.stats.rates` applies.
            acted += 1
            if planned.action == planned.ground_truth:
                correct += 1

        # Visible to a poller immediately, not just once the whole run ends.
        progress_session = Session(engine)
        try:
            progress_row = progress_session.get(SimulationRun, run_id)
            progress_row.decisions_submitted = submitted
            progress_session.commit()
        finally:
            progress_session.close()

    accuracy = (correct / acted) if acted else None
    wilson = wilson_lower_bound(correct, acted) if acted else None
    completed_at = datetime.now(UTC)

    if failure is None:
        # A human answers the deferrals this run produced. Without this the
        # escalations sit unruled for ever, which is a hole in the record the
        # governance audit agent objects to by design — and the objection
        # downgrades every INCREASE to a HOLD, so no run could produce an
        # approval request. Ruling is also the only source of
        # `human_agreement`, the trust score's fourth component.
        #
        # A second pass, after every decision is committed, rather than ruling
        # inline: a human rules on an escalation *after* the agent deferred,
        # never in the same breath, and `simulator/arc.py` models it the same
        # way for the same reason.
        _rule_on_the_escalations_this_run_produced(engine, escalated_ids, plan, run_id)
        # Before the run is marked completed, not after. A client that polls and
        # sees `completed` should be able to read the agent's new limit in the
        # very next request; applying afterwards left a window where the run was
        # done and the clawback had not landed yet.
        #
        # Guarded at the call site as well as inside: the decisions are already
        # committed and the run genuinely succeeded, so nothing here — including
        # a bug in the clawback path itself — may turn it into a failure.
        try:
            _act_on_what_the_run_earned(run_id, engine, agent_id)
        except Exception as exc:  # noqa: BLE001 - a successful run stays successful
            _log_recommendation_attempt_failed(engine, run_id, agent_id, exc)

    final_session = Session(engine)
    try:
        final_row = final_session.get(SimulationRun, run_id)
        final_row.decisions_submitted = submitted
        final_row.completed_at = completed_at
        final_row.accuracy = accuracy
        final_row.wilson_lower_bound = wilson
        if failure is not None:
            final_row.status = RunStatus.FAILED
            final_row.error_message = failure
        else:
            final_row.status = RunStatus.COMPLETED
        append_entry(
            final_session,
            id=f"log-{uuid.uuid4().hex[:12]}",
            ts=completed_at,
            actor="system",
            actor_type="system",
            event_type="simulation_run.failed" if failure is not None else "simulation_run.completed",
            entity_type="simulation_run",
            entity_id=run_id,
            payload={
                "phase": phase.value,
                "seed": seed,
                "requested_count": invoice_count,
                "decisions_submitted": submitted,
                "accuracy": accuracy,
                "wilson_lower_bound": wilson,
                "error": failure,
            },
        )
        final_session.commit()
    finally:
        final_session.close()



def _rule_on_the_escalations_this_run_produced(
    engine: Engine, escalated_ids: list[str], plan: list[PlannedDecision], run_id: str
) -> None:
    """Answer every deferral this run made, one transaction each.

    The human is modelled as the reference standard: they rule the way ground
    truth says. Agreement therefore measures whether the *agent's* own
    judgement (`recommended_action`) matched the reviewer's — which is the
    question `human_agreement` is asking — rather than measuring the reviewer.
    `simulator/arc.py` models the human exactly the same way.

    Never fails the run. The decisions are committed and the run genuinely
    succeeded; an unruled escalation is a thinner record, not a wrong one, and
    a later ruling can still fill it in.
    """
    if not escalated_ids:
        return

    from app.api.v1.decisions import rule_on_decision
    from app.deps import _STUB_USERS
    from app.schemas.decision import DecisionRuling
    from app.schemas.user import Role

    ground_truth_by_invoice = {p.invoice_id: p.ground_truth for p in plan}
    reviewer = _STUB_USERS[Role.REVIEWER]

    # One session for the whole pass. `rule_on_decision` commits each ruling
    # itself, so each is still its own transaction and a failure part-way
    # through keeps the rulings already made — but opening a connection per
    # ruling cost more than the rulings did. A 200-invoice run escalates
    # roughly half its invoices, so this is ~100 connections saved per run.
    session = Session(engine)
    try:
        for decision_id in escalated_ids:
            try:
                decision = session.get(Decision, decision_id)
                if decision is None:
                    continue
                ruling = ground_truth_by_invoice.get(decision.invoice_id)
                if ruling is None:
                    continue
                rule_on_decision(
                    decision_id=decision_id,
                    body=DecisionRuling(
                        ruling=ruling,
                        reason=f"simulated review for run {run_id}",
                    ),
                    user=reviewer,
                    db=session,
                )
            except Exception:  # noqa: BLE001 - a thinner record must not fail a good run
                session.rollback()
    finally:
        session.close()


def _pending_request_already_covers(
    session: Session, agent_id: str, proposed_limit: int
) -> bool:
    """Is a *live* approval request for exactly this limit already waiting?

    "Does any pending recommendation exist" was the wrong question, and asking
    it broke the thing it was meant to protect. `app/seed.py` ships agent-01
    with a PENDING increase to INR 5,000 — valid when seeded, since the agent
    starts at INR 2,500 — so once a clawback moved that agent down, every
    later run saw a pending row, assumed its own request was a duplicate, and
    wrote nothing. The approvals queue then showed one stale card forever
    while the agent detail page reported `direction=INCREASE`, and no new
    request could ever appear.

    A pending row proposing a *different* limit is not a duplicate, it is out
    of date: it was written against evidence that has since changed. It is
    marked `SUPERSEDED` — the state `shared/enums.py` already defines for
    exactly this ("invalidated by a newer one before a human ever ruled on
    it") and which no code had ever written — so the queue holds at most one
    live request per agent instead of a pile of contradictory ones.

    That also defuses a real hazard. `approve_recommendation` applies
    `row.proposed_limit` whenever it differs from the agent's current limit,
    with no check that the proposal still sits one rung away. Approving the
    stale INR 5,000 card while the agent sat at INR 1,000 would have jumped
    three rungs in a single click, against ADR-0004's "exactly one rung per
    change". Superseding stale rows removes the card before anyone can click
    it; the missing guard inside the approve path is flagged in the decision
    log and is not this function's to add.
    """
    from shared.enums import RecommendationStatus

    from app.models import Recommendation

    rows = (
        session.execute(
            select(Recommendation)
            .where(Recommendation.agent_id == agent_id)
            .where(Recommendation.status == RecommendationStatus.PENDING)
        )
        .scalars()
        .all()
    )

    covered = False
    for row in rows:
        if row.proposed_limit == proposed_limit:
            covered = True
        else:
            row.status = RecommendationStatus.SUPERSEDED
    return covered


def _act_on_what_the_run_earned(run_id: str, engine: Engine, agent_id: str) -> None:
    """Turn the run's own evidence into a recommendation, if it earned one.

    A run records decisions and stops. That left a real governance hole: a
    degraded run could push drift to CRITICAL, the trust evaluation would
    correctly read CLAWBACK, and the agent would keep its full limit
    indefinitely — because a clawback only applies when a *recommendation* is
    generated, and nothing generated one. Detection without action.

    ADR-0004 is explicit that a reduction needs no human authorization, so
    nothing should have to poke the system for one to take effect. Generating
    the recommendation here closes that: `generate_recommendation` applies a
    CLAWBACK immediately and leaves an INCREASE pending, which is exactly the
    asymmetry we want.

    Both directions, not just clawbacks. Restricting this to CLAWBACK left
    the other half of ADR-0004 with no producer at all: a good run would
    raise the trust score until the ladder read INCREASE, and nothing
    anywhere created the recommendation, so no approval request ever appeared
    and the dashboard showed an increase that could not be acted on. The only
    code in the whole project that generated one was the /demo console.

    `generate_recommendation` already draws exactly the line we want — it
    applies a CLAWBACK in the same transaction and leaves an INCREASE
    `PENDING` — so handing it both directions produces the asymmetry rather
    than bypassing it. A run still never raises a limit by itself.

    A run that earns nothing (`HOLD`) writes nothing. And an agent that
    already has a pending recommendation does not get a second one: re-running
    a simulation is something a person does freely while rehearsing, and
    stacking near-identical approval requests would bury the one that matters.

    Never fails the run. The run itself succeeded; the decisions are recorded
    and a later evaluation would reach the same conclusion. A governance
    outage — no recording in cached mode, no network in live mode — must not
    retroactively mark a completed run as failed.
    """
    from shared.enums import Direction

    from app.services.governance import generate_recommendation
    from app.services.trust import compute_and_persist_trust_evaluation

    session = Session(engine)
    try:
        agent = session.get(Agent, agent_id)
        if agent is None:
            return
        evaluation, _ = compute_and_persist_trust_evaluation(session, agent)
        if evaluation.direction not in (Direction.CLAWBACK, Direction.INCREASE):
            session.commit()
            return
        if evaluation.direction is Direction.INCREASE and _pending_request_already_covers(
            session, agent_id, evaluation.recommended_limit
        ):
            # The same request is already waiting on a human. Asking twice for
            # one rung tells nobody anything new.
            session.commit()
            return
        generate_recommendation(session, agent)
        session.commit()
    except Exception as exc:  # noqa: BLE001 - a governance outage must not fail a completed run
        session.rollback()
        _log_recommendation_attempt_failed(engine, run_id, agent_id, exc)
    finally:
        session.close()


def _log_recommendation_attempt_failed(
    engine: Engine, run_id: str, agent_id: str, exc: Exception
) -> None:
    """Record that the run finished but its recommendation was never written.

    Swallowing this silently would be the worst outcome: an agent that earned a
    clawback and did not get one, or an increase nobody was ever asked to
    approve, with no trace of why either went missing.
    """
    session = Session(engine)
    try:
        append_entry(
            session,
            id=f"log-{uuid.uuid4().hex[:12]}",
            ts=datetime.now(UTC),
            actor="system",
            actor_type="system",
            event_type="simulation_run.recommendation_not_generated",
            entity_type="simulation_run",
            entity_id=run_id,
            payload={
                "agent_id": agent_id,
                "error": f"{type(exc).__name__}: {exc}",
                "reason": (
                    "The run completed and its decisions are recorded, but the "
                    "clawback they earned could not be applied. A later "
                    "evaluation will reach the same conclusion."
                ),
            },
        )
        session.commit()
    except Exception:  # noqa: BLE001 - nothing useful left to do
        session.rollback()
    finally:
        session.close()
