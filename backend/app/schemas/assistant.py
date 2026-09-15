"""Request/response models for `POST /api/v1/assistant/chat`.

No `shared/` equivalent — the assistant is a backend-local feature (a help
panel over the API's own data), not a cross-lane contract the trust or
governance lanes need to agree on.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AssistantChatRequest(BaseModel):
    """`agent_id` absent (or `null`) is the general scope; present, it is the
    agent-scoped conversation — see `app/api/v1/assistant.py` for what each
    scope fetches.

    `page` is the route the user is looking at (e.g. `/approvals`,
    `/agents/agent-01`). It only selects which page guide the assistant reads
    (`app/services/page_guides.py`); the string itself never reaches the model,
    and an unknown route falls back to the system overview alone.
    """

    messages: list[AssistantMessage] = Field(min_length=1)
    agent_id: str | None = None
    page: str | None = Field(default=None, max_length=200)


class AssistantSource(BaseModel):
    """One citation: a guide the reply was grounded in. `doc` is `"Page guide"`
    and `section` is that guide's title (e.g. `"Approvals"`) — see
    `app/services/page_guides.py`.
    """

    doc: str
    section: str


class AssistantChatResponse(BaseModel):
    reply: str
    sources: list[AssistantSource]
