"""Pure planning helpers for batch status updates.

The old ``ItemService.batch_update_status`` iterated the raw ``ids`` argument
directly and mutated each record in place. That meant ``None`` raised on
iteration, a bare string was iterated character-by-character, duplicate ids were
processed twice, an unbounded list could stall the process, and the in-place
mutation aliased whatever the fake DB returned. The I/O-free parts of that logic
live here so they can be tested without a database.
"""

from datetime import datetime
from typing import Any, Iterable, List, Mapping, Optional, Tuple

from .dedup import dedupe_preserving_order
from .errors import ItemDataError

# Upper bound on ids processed in a single call. Prevents an accidental
# multi-million-id request from monopolising the worker.
MAX_BATCH_SIZE = 1000

# plan_update outcomes.
ACTION_UPDATE = "update"
ACTION_SKIPPED = "skipped"
ACTION_FAILED = "failed"


def normalize_ids(ids: Any) -> List[Any]:
    """Coerce the ids argument into a de-duplicated list preserving order.

    ``None`` becomes an empty batch. Strings/bytes are rejected explicitly so a
    single id passed as ``"42"`` is not silently iterated into ``["4", "2"]``.
    Mappings contribute their keys. Anything non-iterable raises
    ``ItemDataError``. De-duplication tolerates unhashable identifiers (e.g. a
    composite ``list``/``dict`` id) instead of raising ``TypeError``.
    """
    if ids is None:
        return []
    if isinstance(ids, (str, bytes)):
        raise ItemDataError("ids must be a collection of identifiers, not a string")
    if isinstance(ids, Mapping):
        candidate: Iterable[Any] = ids.keys()
    elif isinstance(ids, Iterable):
        candidate = ids
    else:
        raise ItemDataError("ids must be an iterable of identifiers")

    return list(dedupe_preserving_order(candidate))


def enforce_batch_limit(ids: List[Any], limit: int = MAX_BATCH_SIZE) -> None:
    if len(ids) > limit:
        raise ItemDataError(
            f"batch size {len(ids)} exceeds the maximum of {limit}"
        )


def plan_update(record: Any, new_status: str) -> Tuple[str, Optional[str]]:
    """Decide what should happen to a single record, without touching it.

    Returns ``(action, reason)`` where ``action`` is one of the ``ACTION_*``
    constants and ``reason`` explains a non-update outcome.
    """
    if record is None:
        return ACTION_FAILED, "not found"
    current = record.get("status") if isinstance(record, Mapping) else None
    if current == new_status:
        return ACTION_SKIPPED, "already in state"
    return ACTION_UPDATE, None


def apply_update(
    record: Mapping,
    new_status: str,
    updated_by: str,
    *,
    now: Optional[datetime] = None,
) -> dict:
    """Return a *new* record dict with the status transition applied.

    Copies rather than mutates so the caller's stored object is never aliased.
    """
    reference = now or datetime.utcnow()
    updated = dict(record)
    updated["status"] = new_status
    updated["updated_by"] = updated_by
    updated["updated_at"] = reference
    return updated
