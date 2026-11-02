"""Pagination helpers for offset/limit slicing."""

from __future__ import annotations

from typing import Sequence, TypeVar


T = TypeVar("T")


def paginate_offset_limit(items: Sequence[T], offset: int = 0, limit: int = 100) -> list[T]:
    """Return a paginated slice from ``items`` using offset/limit."""
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    return list(items[offset : offset + limit])
