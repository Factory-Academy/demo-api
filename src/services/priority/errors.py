"""Exceptions raised by the priority-strategy package."""


class PriorityError(Exception):
    """Base class for all priority-strategy errors."""


class UnknownStrategyError(PriorityError):
    """Raised when the factory is asked for a strategy it does not know."""

    def __init__(self, name: str, available: list):
        self.name = name
        self.available = list(available)
        known = ", ".join(sorted(self.available)) or "<none>"
        super().__init__(
            f"Unknown priority strategy {name!r}. Available strategies: {known}."
        )


class InvalidItemError(PriorityError):
    """Raised when an item cannot be scored because its fields are unusable."""

    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)
