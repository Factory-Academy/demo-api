"""Exceptions raised by the priority-strategy package."""

from __future__ import annotations

from typing import Iterable


class PriorityError(Exception):
    """Base class for every error raised by this package."""


class UnknownStrategyError(PriorityError):
    """Raised when the factory is asked for a strategy name it does not know.

    :attr:`available` lists the names that *are* registered, so callers (and
    error messages) can suggest a valid choice.
    """

    def __init__(self, name: str, available: Iterable[str] = ()):
        self.name = name
        self.available = tuple(available)
        known = ", ".join(self.available) if self.available else "(none registered)"
        super().__init__(
            f"unknown priority strategy {name!r}; available: {known}"
        )
