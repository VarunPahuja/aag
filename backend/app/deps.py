"""Shared FastAPI dependencies: identity, role checks, and the DB-session stub.

No real auth or database exists yet (docs/DEADLINES.md: persistence lands
Fri 28 Aug - Mon 31 Aug). What's here is deliberately the *shape* these will
have once real: a header-based stub identity today, a real JWT later behind
the same `current_user` signature; a `get_db_session` stub that nothing
calls yet, so the day a real session exists, every route that will need one
already has the right parameter.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.schemas.envelope import ErrorBody
from app.schemas.user import CurrentUser, Role

# Stub users, one per role, keyed by the header value a caller sends. Real JWT
# claims replace this table; the CurrentUser shape it produces does not change.
_STUB_USERS: dict[Role, CurrentUser] = {
    Role.ADMIN: CurrentUser(user_id="user-admin-01", email="admin@aagp.dev", role=Role.ADMIN),
    Role.REVIEWER: CurrentUser(
        user_id="user-reviewer-01", email="reviewer@aagp.dev", role=Role.REVIEWER
    ),
    Role.AUDITOR: CurrentUser(user_id="user-auditor-01", email="auditor@aagp.dev", role=Role.AUDITOR),
}


def current_user(
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> CurrentUser:
    """Read `X-User-Role` and return the stubbed user for that role.

    Defaults to ADMIN when the header is absent — a dev convenience so
    `/docs` and a bare `curl` work without extra setup. Any recognized role
    string works case-insensitively; an unrecognized one is a 401, not a
    silent fallback (the same "fail loud on a typo" reasoning
    `governance/governance/agents/base.py`'s `require_stub_mode` already
    uses for `GOVERNANCE_MODE` — an unnoticed typo here would mean
    "everyone got admin" instead of "the demo obviously isn't working").
    """
    if x_user_role is None:
        return _STUB_USERS[Role.ADMIN]
    try:
        role = Role(x_user_role.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=ErrorBody(
                code="invalid_role_header",
                message=f"X-User-Role {x_user_role!r} is not a recognized role.",
                detail={"expected_one_of": [r.value for r in Role]},
            ).model_dump(),
        ) from exc
    return _STUB_USERS[role]


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


def require_role(*allowed: Role):
    """FastAPI's idiom for a role-check decorator: a dependency factory.

    `Depends(require_role(Role.ADMIN))` on a route raises 403 for anyone
    whose stubbed role isn't in `allowed`. Applied now, on every
    state-changing endpoint, even though the identity behind it is a stub —
    docs/lanes/vp.md: "the role-check decorator exists and is applied from
    the start" so the shape is already right when real auth lands.
    """

    def _check(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=ErrorBody(
                    code="forbidden",
                    message=f"Role {user.role.value!r} may not perform this action.",
                    detail={"required_one_of": [r.value for r in allowed]},
                ).model_dump(),
            )
        return user

    return _check


def get_db_session() -> Generator[None, None, None]:
    """Placeholder for the SQLAlchemy session dependency persistence will add.

    Nothing in this branch calls it — this branch ships the contract, not
    persistence (docs/DEADLINES.md: Fri 28 Aug / Mon 31 Aug). It exists now,
    unused, so the parameter shape (`db: Annotated[Session, Depends(get_db_session)]`)
    is already the one every route will actually take, rather than being
    retrofitted later. Calling it before persistence lands is a programming
    error, not a runtime path any current endpoint can reach.
    """
    raise NotImplementedError(
        "No database session yet — persistence lands Fri 28 Aug / Mon 31 Aug "
        "per docs/lanes/vp.md. This stub exists for its shape, not to be called."
    )
    yield  # pragma: no cover - unreachable; makes this a generator function
