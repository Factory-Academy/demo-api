from typing import List

from src.domain import WidgetRecord, WidgetStats
from src.utils.caching import ttl_cache


class WidgetService:
    def __init__(self):
        self.widgets: List[WidgetRecord] = []

    @ttl_cache(ttl=60, maxsize=50)
    def get_complex_widget_stats(self, widget_id: int) -> WidgetStats:
        """
        Simulate a heavy calculation for widget statistics.
        """
        # In a real app, this might query multiple tables or external APIs
        return WidgetStats(
            id=widget_id,
            complexity_score=widget_id * 1.5,
            last_analyzed="2023-10-14T12:00:00Z",
        )

    def list_widgets(self) -> List[WidgetRecord]:
        return self.widgets
