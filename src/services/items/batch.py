"""Batch status updates split into pure planning and effectful application.

The decision about what to do with each record is pure and unit-testable;
only :func:`batch_update_status` touches the datastore.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

UPDATE = "update"
SKIP = "skip"
MISSING = "missing"

# Guards against unbounded memory use when a caller passes a huge id list.
DEFAULT_CHUNK_SIZE = 500


def normalize_ids(ids: Optional[Iterable[Any]]) -> List[Any]:
    """Return a de-duplicated id list, preserving order and dropping ``None``.

    A ``None`` or non-iterable argument yields an empty list rather than
    raising.
    """
    if ids is None:
        return []
    if isinstance(ids, (str, bytes)):
        # A bare string is almost certainly a mistake, not a sequence of ids.
        return []
    try:
        iterator = iter(ids)
    except TypeError:
        return []
    seen: set = set()
    ordered: List[Any] = []
    for identifier in iterator:
        if identifier is None:
            continue
        try:
            already_seen = identifier in seen
        except TypeError:
            # Unhashable id; keep it but skip de-duplication for it.
            ordered.append(identifier)
            continue
        if already_seen:
            continue
        seen.add(identifier)
        ordered.append(identifier)
    return ordered


def chunk(items: List[Any], size: int = DEFAULT_CHUNK_SIZE) -> Iterable[List[Any]]:
    """Yield successive chunks of ``items`` of at most ``size`` entries."""
    if size <= 0:
        size = DEFAULT_CHUNK_SIZE
    for start in range(0, len(items), size):
        yield items[start : start + size]


def plan_record_change(record: Optional[Mapping[str, Any]], new_status: str) -> str:
    """Decide the action for a single fetched record (pure)."""
    if record is None:
        return MISSING
    if record.get("status") == new_status:
        return SKIP
    return UPDATE


def apply_status_change(
    record: Dict[str, Any],
    new_status: str,
    updated_by: str,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return ``record`` mutated with the new status and audit fields."""
    record["status"] = new_status
    record["updated_by"] = updated_by
    record["updated_at"] = now if now is not None else datetime.utcnow()
    return record


def batch_update_status(
    db: Any,
    ids: Optional[Iterable[Any]],
    new_status: str,
    updated_by: str,
    *,
    now: Optional[datetime] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Dict[str, List[Any]]:
    """Apply ``new_status`` to each stored record identified by ``ids``.

    Returns a report of updated ids and skipped/failed entries with reasons.
    An empty, ``None``, or malformed id list yields an empty report instead of
    raising.
    """
    results: Dict[str, List[Any]] = {"updated": [], "failed": [], "skipped": []}

    if not isinstance(new_status, str) or new_status.strip() == "":
        for identifier in normalize_ids(ids):
            results["failed"].append({"id": identifier, "reason": "invalid status"})
        return results

    for batch in chunk(normalize_ids(ids), chunk_size):
        for identifier in batch:
            record = db.get(identifier)
            action = plan_record_change(record, new_status)
            if action == MISSING:
                results["failed"].append({"id": identifier, "reason": "not found"})
            elif action == SKIP:
                results["skipped"].append(
                    {"id": identifier, "reason": "already in state"}
                )
            else:
                updated = apply_status_change(
                    record, new_status, updated_by, now=now
                )
                db.save(updated)
                results["updated"].append(identifier)
    return results
