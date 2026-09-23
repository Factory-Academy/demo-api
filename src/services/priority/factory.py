"""Factory and registry for priority strategies.

Callers ask for a strategy by name instead of importing a concrete class, so
the choice can come from config, a request parameter, or a feature flag without
touching call sites.
"""

from __future__ import annotations

from typing import Callable, Dict

from .errors import UnknownStrategyError
from .protocol import PriorityStrategy
from .strategies import DeadlineAwareStrategy, WeightedScoreStrategy

# Registered factories keyed by strategy name. Values are zero-arg callables so
# each lookup yields a fresh instance with default options.
_REGISTRY: Dict[str, Callable[[], PriorityStrategy]] = {
    WeightedScoreStrategy.name: WeightedScoreStrategy,
    DeadlineAwareStrategy.name: DeadlineAwareStrategy,
}

DEFAULT_STRATEGY = WeightedScoreStrategy.name


def available_strategies() -> list:
    """Names of every registered strategy, sorted for stable output."""
    return sorted(_REGISTRY)


def register_strategy(
    name: str, factory: Callable[[], PriorityStrategy], *, replace: bool = False
) -> None:
    """Add a strategy factory to the registry.

    Set ``replace=True`` to override an existing name; otherwise a duplicate
    registration is rejected so accidental shadowing is caught early.
    """
    if not name:
        raise ValueError("strategy name must be a non-empty string")
    if name in _REGISTRY and not replace:
        raise ValueError(f"strategy {name!r} is already registered")
    _REGISTRY[name] = factory


def create_priority_strategy(name: str = DEFAULT_STRATEGY, **options) -> PriorityStrategy:
    """Instantiate the strategy registered under ``name``.

    ``options`` are forwarded to the underlying constructor, so
    ``create_priority_strategy("deadline", high_within_days=5)`` works. Raises
    :class:`UnknownStrategyError` for an unregistered name.
    """
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise UnknownStrategyError(name, available_strategies()) from None
    return factory(**options)
