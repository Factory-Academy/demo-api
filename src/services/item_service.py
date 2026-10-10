"""Backward-compatible shim.

The item business logic now lives in the :mod:`src.services.items` package,
split into a pure core (priority, validation, status) and a thin adapter. This
module preserves the historical import path::

    from src.services.item_service import ItemService
"""
from src.services.items import ItemService, ValidationResult

__all__ = ["ItemService", "ValidationResult"]
