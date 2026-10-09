from datetime import datetime
from typing import Dict, List, Optional


def build_timestamped_record(
    payload: Dict, record_id: int, now: Optional[datetime] = None
) -> Dict:
    timestamp = now or datetime.utcnow()
    return {
        **payload,
        "id": record_id,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def find_record_by_id(records: List[Dict], record_id: int) -> Optional[Dict]:
    record_index = find_record_index_by_id(records, record_id)
    if record_index is None:
        return None
    return records[record_index]


def find_record_index_by_id(records: List[Dict], record_id: int) -> Optional[int]:
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        if record.get("id") == record_id:
            return index
    return None
