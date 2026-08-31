"""Model-layer enforcement for the two invariants docs/lanes/vp.md states in
prose rather than in a constraint:

- **`policy_versions` and `audit_log` are append-only.** No update path
  anywhere in this codebase — enforced here so that stays true even if a
  future caller reaches for `session.merge()` or sets an attribute directly,
  not just because nobody happened to write an UPDATE.
- **`agents.current_limit`/`current_rung` never change without a new
  `policy_versions` row in the same transaction.** `ck_agents_rung_matches_limit`
  (`app/models/agents.py`) catches an *inconsistent* pair; it cannot catch a
  *consistent* pair written without a paired version row, because from the
  database's perspective that row looks perfectly fine on its own. This hook
  closes that gap.

Both are `before_flush` checks on every `Session`, not something a particular
call site opts into — a caller has to go out of their way (bypassing the ORM
session, e.g. raw SQL) to get around them, which is a deliberate, visible
choice rather than an easy accident. This is model-layer enforcement, not the
Policy Engine (`backend/app/policy/`, ADR-0003, ADR-0014): it guards how the
database gets written to; it never decides whether an action is permitted.

Importing this module registers the listener as a side effect — `app/models/
__init__.py` does so once, after every model it inspects (`Agent`,
`PolicyVersion`, `AuditLogEntry`) is already defined.
"""

from __future__ import annotations

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.agents import Agent
from app.models.audit_log import AuditLogEntry
from app.models.policy_versions import PolicyVersion

_APPEND_ONLY_TYPES = (PolicyVersion, AuditLogEntry)


class ImmutableRowError(RuntimeError):
    """Raised when a flush would UPDATE or DELETE an append-only row."""


class PolicyVersionRequiredError(RuntimeError):
    """Raised when `Agent.current_limit`/`current_rung` changed in this flush
    without a new `PolicyVersion` for the same agent in the same flush."""


def _changed_agent_ids(session: Session) -> set[str]:
    changed: set[str] = set()
    for obj in session.dirty:
        if not isinstance(obj, Agent):
            continue
        state = inspect(obj)
        limit_changed = state.attrs.current_limit.history.has_changes()
        rung_changed = state.attrs.current_rung.history.has_changes()
        if limit_changed or rung_changed:
            changed.add(obj.id)
    return changed


@event.listens_for(Session, "before_flush")
def _enforce_append_only_and_paired_limit_changes(session, flush_context, instances) -> None:
    for obj in session.dirty:
        if isinstance(obj, _APPEND_ONLY_TYPES):
            raise ImmutableRowError(
                f"{type(obj).__name__} rows are append-only; cannot modify id={obj.id!r} "
                "(docs/lanes/vp.md)."
            )
    for obj in session.deleted:
        if isinstance(obj, _APPEND_ONLY_TYPES):
            raise ImmutableRowError(
                f"{type(obj).__name__} rows are append-only; cannot delete id={obj.id!r} "
                "(docs/lanes/vp.md)."
            )

    changed_agent_ids = _changed_agent_ids(session)
    if not changed_agent_ids:
        return

    versioned_agent_ids = {obj.agent_id for obj in session.new if isinstance(obj, PolicyVersion)}
    missing = changed_agent_ids - versioned_agent_ids
    if missing:
        raise PolicyVersionRequiredError(
            "agents.current_limit/current_rung changed for agent(s) "
            f"{sorted(missing)} without a new policy_versions row in the same "
            "transaction (docs/lanes/vp.md: 'Never update agents.current_limit "
            "without writing a policy_versions row in the same transaction'). "
            "Use app.models.policy_versions.apply_policy_version()."
        )
