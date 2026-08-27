"""The one pagination envelope, and the query params every list endpoint shares."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, TypeVar

from fastapi import Query

from app.schemas.envelope import Page

T = TypeVar("T")

PageParam = Annotated[int, Query(ge=1, description="1-indexed page number")]
PageSizeParam = Annotated[int, Query(ge=1, le=200, description="Items per page")]


def paginate(items: Sequence[T], page: int, page_size: int) -> Page[T]:
    total = len(items)
    start = (page - 1) * page_size
    page_items = list(items[start : start + page_size])
    return Page[T](items=page_items, total=total, page=page, page_size=page_size)
