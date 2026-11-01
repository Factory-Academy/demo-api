"""The strategy contract.

Priority strategies are defined structurally with :class:`typing.Protocol`:
anything that exposes a ``name`` and an ``assess`` method satisfies the
contract, with no base class to inherit. That keeps implementations (and test
doubles) free of boilerplate while still giving static checkers something to
verify against.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.services.priority.models import PriorityAssessment, PriorityInput


@runtime_checkable
class PriorityStrategy(Protocol):
    """Turns the facts about an item into a :class:`PriorityAssessment`.

    Implementations must be pure with respect to their input: given the same
    :class:`PriorityInput` (and clock reading) they must return the same
    assessment, with no side effects.
    """

    @property
    def name(self) -> str:
        """Stable identifier used by the factory registry and in results."""
        ...

    def assess(self, item: PriorityInput) -> PriorityAssessment:
        ...
