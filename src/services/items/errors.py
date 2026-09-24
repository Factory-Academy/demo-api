"""Error types raised by the item data-processing helpers."""


class ItemDataError(ValueError):
    """Raised when item data is malformed in a way the caller must fix.

    Coercion helpers degrade gracefully by falling back to safe defaults, so
    this is reserved for guardrail violations that would otherwise silently
    corrupt a batch (a missing target status, a non-iterable id collection, or
    a batch larger than the configured limit).
    """
