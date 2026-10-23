"""Priority scoring and classification for items.

Public helpers compose the pure pieces in :mod:`normalization`,
:mod:`scoring`, and :mod:`classification` into the behaviour the service layer
depends on.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from src.services.priority.classification import classify_score
from src.services.priority.scoring import score_item

__all__ = ["classify_score", "score_item", "calculate_priority"]


def calculate_priority(
    item: Optional[Mapping[str, Any]], *, now: Optional[datetime] = None
) -> str:
    """Return the priority label for a raw ``item`` mapping."""
    return classify_score(score_item(item, now=now))
