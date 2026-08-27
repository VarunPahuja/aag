"""Cross-cutting response shapes used by every endpoint in the API.

One pagination envelope, one error body — decided once here, applied
everywhere else (docs/lanes/vp.md, "Cross-cutting").
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Every list endpoint returns this shape. No endpoint returns a bare list."""

    items: list[T]
    total: int = Field(ge=0, description="Total matching records, independent of page size")
    page: int = Field(ge=1, description="1-indexed page number")
    page_size: int = Field(ge=1, description="Items per page, as requested")


class ErrorBody(BaseModel):
    """Every non-2xx response returns this shape as its JSON body.

    `code` is a short machine-readable slug (e.g. "not_found", "forbidden",
    "validation_error") for client branching; `message` is one sentence a human
    reads; `detail` carries whatever extra structure the specific failure needs
    (field errors, the resource id that was missing, etc.) and may be null.
    """

    code: str
    message: str
    detail: object | None = None
