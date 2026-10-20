"""Factory and registry for priority strategies.

Callers ask for a strategy by name instead of importing a concrete class,
which keeps the selection decoupled from the usage site (e.g. a config value
or request parameter can pick the strategy). New strategies can opt in with
:func:`register_strategy` without touching this module.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from src.services.priority.base import PriorityStrategy
from src.services.priority.strategies import DeadlineStrategy, WeightedScoreStrategy

StrategyFactory = Callable[..., PriorityStrategy]

DEFAULT_STRATEGY = "weighted"

_REGISTRY: Dict[str, StrategyFactory] = {
    WeightedScoreStrategy.name: WeightedScoreStrategy,
    DeadlineStrategy.name: DeadlineStrategy,
}


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def available_strategies() -> List[str]:
    """Return the registered strategy names, sorted for stable output."""
    return sorted(_REGISTRY)


def register_strategy(
    name: str, factory: StrategyFactory, *, overwrite: bool = False
) -> None:
    """Register a new strategy factory under ``name``.

    Raises ``ValueError`` on an empty name or a collision unless ``overwrite``
    is set, so an accidental double-registration fails loudly.
    """
    key = _normalize(name)
    if not key:
        raise ValueError("strategy name must be a non-empty string")
    if key in _REGISTRY and not overwrite:
        raise ValueError(f"strategy '{key}' is already registered")
    _REGISTRY[key] = factory


def create_priority_strategy(
    name: str = DEFAULT_STRATEGY, **kwargs
) -> PriorityStrategy:
    """Instantiate a registered strategy by name.

    Extra keyword arguments are forwarded to the strategy constructor, so
    callers can tune weights or windows at creation time. Raises ``ValueError``
    with the list of known names when ``name`` is not registered.
    """
    key = _normalize(name) or DEFAULT_STRATEGY
    try:
        factory = _REGISTRY[key]
    except KeyError:
        raise ValueError(
            f"unknown priority strategy '{name}'. "
            f"available: {', '.join(available_strategies())}"
        ) from None
    return factory(**kwargs)
