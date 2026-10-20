"""Pluggable priority-scoring strategies.

Public surface:

* :class:`PriorityLevel`, :class:`PriorityContext`, :class:`PriorityResult`,
  :class:`PriorityStrategy` - the shared vocabulary and protocol.
* :class:`WeightedScoreStrategy`, :class:`DeadlineStrategy` - implementations.
* :func:`create_priority_strategy`, :func:`register_strategy`,
  :func:`available_strategies` - the factory/registry entry points.
"""

from src.services.priority.base import (
    PriorityContext,
    PriorityLevel,
    PriorityResult,
    PriorityStrategy,
)
from src.services.priority.factory import (
    DEFAULT_STRATEGY,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from src.services.priority.strategies import DeadlineStrategy, WeightedScoreStrategy

__all__ = [
    "PriorityContext",
    "PriorityLevel",
    "PriorityResult",
    "PriorityStrategy",
    "WeightedScoreStrategy",
    "DeadlineStrategy",
    "create_priority_strategy",
    "register_strategy",
    "available_strategies",
    "DEFAULT_STRATEGY",
]
