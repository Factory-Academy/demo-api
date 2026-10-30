"""Pluggable priority strategies behind a factory.

A priority *strategy* turns the facts about an item into a
:class:`PriorityAssessment` (a level plus a score and a short reason). Two
strategies ship today and share the :class:`PriorityStrategy` protocol, so they
are interchangeable:

* ``weighted`` -- a weighted sum of urgency, a critical flag and age
  (:class:`WeightedScoreStrategy`); the original scoring heuristic.
* ``sla`` -- time-to-deadline (:class:`SlaDeadlineStrategy`).

Pick one by name through the factory::

    from src.services.priority import PriorityInput, create_priority_strategy

    strategy = create_priority_strategy("sla")
    assessment = strategy.assess(PriorityInput.from_item(item))
    assessment.level  # -> PriorityLevel.HIGH

See ``docs/priority-strategy-NOTES.md`` for the design rationale and a
comparison of the two approaches.
"""

from src.services.priority.errors import PriorityError, UnknownStrategyError
from src.services.priority.factory import (
    DEFAULT_STRATEGY,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from src.services.priority.models import (
    PriorityAssessment,
    PriorityInput,
    PriorityLevel,
)
from src.services.priority.protocol import PriorityStrategy
from src.services.priority.sla import SlaDeadlineConfig, SlaDeadlineStrategy
from src.services.priority.weighted import WeightedScoreConfig, WeightedScoreStrategy

__all__ = [
    "PriorityError",
    "UnknownStrategyError",
    "DEFAULT_STRATEGY",
    "available_strategies",
    "create_priority_strategy",
    "register_strategy",
    "PriorityAssessment",
    "PriorityInput",
    "PriorityLevel",
    "PriorityStrategy",
    "SlaDeadlineConfig",
    "SlaDeadlineStrategy",
    "WeightedScoreConfig",
    "WeightedScoreStrategy",
]
