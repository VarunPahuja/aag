"""`users` — docs/lanes/vp.md schema: id, email, role, created_at.

Backs the stubbed identities in `app/deps.py`/`app/schemas/user.py` today
(`Role.ADMIN`/`REVIEWER`/`AUDITOR`); a real row per stub user once
persistence is wired into `current_user` (out of scope for this branch —
"Do NOT wire the API endpoints to the database in this branch").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import enum_column
from app.schemas.user import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[Role] = mapped_column(enum_column(Role), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
