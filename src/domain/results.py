"""Result dataclasses returned by the service layer.

These replace the ad-hoc tuples and nested dict-of-lists the service used to
return, giving callers named, typed access to outcomes.
"""

from dataclasses import dataclass, field
from typing import Iterator, List


@dataclass
class ValidationResult:
    """Outcome of validating an item payload."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    def __iter__(self) -> Iterator:
        # Preserves the previous ``ok, errors = validate_item(...)`` unpacking.
        yield self.is_valid
        yield self.errors


@dataclass
class BatchOutcome:
    """A single id that could not be updated and the reason why."""

    id: int
    reason: str


@dataclass
class BatchUpdateResult:
    """Aggregate result of a batch status update."""

    updated: List[int] = field(default_factory=list)
    failed: List[BatchOutcome] = field(default_factory=list)
    skipped: List[BatchOutcome] = field(default_factory=list)
