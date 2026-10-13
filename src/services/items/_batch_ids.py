"""Helpers for normalizing batch-update ID inputs.

The service accepts IDs from a few caller shapes:
- an iterable of IDs (the normal case)
- a single scalar ID (e.g. ``123`` or ``"abc"``)
- ``None`` (treated as no IDs)

Normalizing those cases in one place keeps the adapter logic simple and
prevents accidental per-character iteration when a single string ID is passed.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def as_id_list(ids: Any) -> list[Any]:
    """Return ``ids`` as a concrete list of IDs.

    ``None`` becomes an empty list. Strings and bytes are treated as scalar IDs
    rather than iterables of characters/bytes.
    """
    if ids is None:
        return []
    if isinstance(ids, (str, bytes, bytearray)):
        return [ids]
    if isinstance(ids, Iterable):
        return list(ids)
    return [ids]
