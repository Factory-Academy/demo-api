from typing import Any


class NotFoundError(LookupError):
    """Raised when a record cannot be found by id."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def find_record_by_id(
    records: list[dict[str, Any]], record_id: int, detail: str
) -> dict[str, Any]:
    """Return the matching record, or raise NotFoundError."""
    for record in records:
        if record.get("id") == record_id:
            return record
    raise NotFoundError(detail)
