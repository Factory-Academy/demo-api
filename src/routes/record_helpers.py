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
    for record in records:
        if record["id"] == record_id:
            return record
    return None
