"""A tiny in-memory repository used by the service layer and tests.

The service only needs ``get`` and ``save``; this provides both over a dict of
:class:`ItemRecord` keyed by id, plus a couple of conveniences for tests.
"""

from typing import Dict, List, Optional

from src.domain.models import ItemRecord


class InMemoryRepository:
    def __init__(self, records: Optional[List[ItemRecord]] = None) -> None:
        self._records: Dict[int, ItemRecord] = {}
        for record in records or []:
            self.save(record)

    def get(self, id: int) -> Optional[ItemRecord]:
        return self._records.get(id)

    def save(self, record: ItemRecord) -> ItemRecord:
        self._records[record.id] = record
        return record

    def list(self) -> List[ItemRecord]:
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)
