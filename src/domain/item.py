from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, List, Mapping, Optional

from src.domain.coercion import (
    coerce_bool,
    coerce_datetime,
    coerce_int,
    ensure_known_fields,
    require,
)


@dataclass(frozen=True)
class ItemRecord:
    """Canonical in-memory representation of a stored item.

    This replaces the loose ``dict`` records that used to be passed between
    the routes and :class:`~src.services.item_service.ItemService`. The type is
    frozen so it is hashable (which lets it be used as a cache key) and so that
    updates go through :meth:`with_changes`, producing a fresh record instead
    of mutating shared state.
    """

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    status: str = "active"
    urgency: int = 0
    is_critical: bool = False
    quantity: int = 0
    due_date: Optional[datetime] = None
    updated_by: Optional[str] = None

    def age_days(self, now: Optional[datetime] = None) -> int:
        """Whole days elapsed since the record was created."""
        reference = now if now is not None else datetime.utcnow()
        return (reference - self.created_at).days

    def with_changes(self, now: Optional[datetime] = None, **changes: Any) -> "ItemRecord":
        """Return a copy with ``changes`` applied and ``updated_at`` refreshed."""
        ensure_known_fields(self, changes)
        stamped = now if now is not None else datetime.utcnow()
        return replace(self, updated_at=stamped, **changes)

    def with_status(
        self, status: str, updated_by: str, now: Optional[datetime] = None
    ) -> "ItemRecord":
        """Return a copy transitioned to ``status`` and attributed to a user."""
        return self.with_changes(status=status, updated_by=updated_by, now=now)

    def to_dict(self) -> dict:
        """Serialize to a plain ``dict`` for response/boundary use."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ItemRecord":
        """Build a record from a loose mapping, coercing timestamp strings.

        Useful when migrating previously persisted ``dict`` payloads. ``id`` and
        ``name`` are required; missing ones raise ``ValueError`` rather than a
        bare ``KeyError``. Numeric, boolean, and date fields are coerced from
        their loose string forms and raise ``ValueError`` when unparseable.
        """
        now = datetime.utcnow()
        return cls(
            id=coerce_int(require(data, "id"), field="id"),
            name=require(data, "name"),
            created_at=coerce_datetime(
                data.get("created_at"), field="created_at", default=now
            ),
            updated_at=coerce_datetime(
                data.get("updated_at"), field="updated_at", default=now
            ),
            description=data.get("description"),
            status=data.get("status", "active"),
            urgency=coerce_int(data.get("urgency", 0), field="urgency"),
            is_critical=coerce_bool(
                data.get("is_critical", False), field="is_critical"
            ),
            quantity=coerce_int(data.get("quantity", 0), field="quantity"),
            due_date=coerce_datetime(
                data.get("due_date"), field="due_date", default=None
            ),
            updated_by=data.get("updated_by"),
        )


@dataclass
class ValidationResult:
    """Outcome of validating an :class:`ItemRecord`."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def raise_for_errors(self) -> None:
        """Raise ``ValueError`` summarizing the errors, if any."""
        if not self.is_valid:
            raise ValueError("; ".join(self.errors))

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(is_valid=True, errors=[])

    @classmethod
    def failed(cls, errors: List[str]) -> "ValidationResult":
        return cls(is_valid=False, errors=list(errors))


@dataclass(frozen=True)
class BatchOutcome:
    """A single id that could not be updated, with the reason why."""

    id: int
    reason: str


@dataclass
class BatchUpdateResult:
    """Structured result of a batch status update."""

    updated: List[int] = field(default_factory=list)
    failed: List[BatchOutcome] = field(default_factory=list)
    skipped: List[BatchOutcome] = field(default_factory=list)

    def mark_updated(self, item_id: int) -> None:
        self.updated.append(item_id)

    def mark_failed(self, item_id: int, reason: str) -> None:
        self.failed.append(BatchOutcome(id=item_id, reason=reason))

    def mark_skipped(self, item_id: int, reason: str) -> None:
        self.skipped.append(BatchOutcome(id=item_id, reason=reason))

    @property
    def total(self) -> int:
        return len(self.updated) + len(self.failed) + len(self.skipped)

    def to_dict(self) -> dict:
        """Serialize to the legacy ``dict`` shape for API responses."""
        return {
            "updated": list(self.updated),
            "failed": [asdict(outcome) for outcome in self.failed],
            "skipped": [asdict(outcome) for outcome in self.skipped],
        }
