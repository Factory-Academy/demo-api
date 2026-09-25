"""Pluggable priority scoring.

Public surface:

    from src.services.priority import create_priority_strategy, PriorityLevel

    strategy = create_priority_strategy("weighted")
    result = strategy.assess(item)
    result.level  # PriorityLevel.HIGH
    result.score  # 55.0
"""

from .errors import InvalidItemError, PriorityError, UnknownStrategyError
from .factory import (
    DEFAULT_STRATEGY,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from .protocol import Item, PriorityLevel, PriorityResult, PriorityStrategy
from .strategies import DeadlineAwareStrategy, WeightedScoreStrategy

__all__ = [
    "create_priority_strategy",
    "register_strategy",
    "available_strategies",
    "DEFAULT_STRATEGY",
    "PriorityStrategy",
    "PriorityLevel",
    "PriorityResult",
    "Item",
    "WeightedScoreStrategy",
    "DeadlineAwareStrategy",
    "PriorityError",
    "UnknownStrategyError",
    "InvalidItemError",
]
