"""The factory that hides concrete strategies behind a name.

Callers ask for a strategy by name (``create_priority_strategy("sla")``)
instead of importing and constructing a concrete class, so swapping the
heuristic is a one-line config change and new strategies can be registered
without touching call sites. The two built-ins are registered on import;
third-party code can add its own with :func:`register_strategy`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from src.services.priority.errors import UnknownStrategyError
from src.services.priority.protocol import PriorityStrategy
from src.services.priority.sla import SlaDeadlineStrategy
from src.services.priority.weighted import WeightedScoreStrategy

#: A registry entry: given keyword config, it builds a ready strategy.
StrategyFactory = Callable[..., PriorityStrategy]

_REGISTRY: Dict[str, StrategyFactory] = {}

#: The strategy used when a caller asks for ``"default"``.
DEFAULT_STRATEGY = "weighted"


def register_strategy(
    name: str, factory: StrategyFactory, *, replace: bool = False
) -> None:
    """Register ``factory`` under ``name``.

    Refuses to clobber an existing name unless ``replace=True``, so an
    accidental duplicate registration fails loudly instead of silently
    shadowing a built-in.
    """
    if not name:
        raise ValueError("strategy name must be a non-empty string")
    if name in _REGISTRY and not replace:
        raise ValueError(
            f"strategy {name!r} is already registered; pass replace=True to override"
        )
    _REGISTRY[name] = factory


def available_strategies() -> Tuple[str, ...]:
    """Return the registered strategy names, sorted."""
    return tuple(sorted(_REGISTRY))


def create_priority_strategy(name: str = DEFAULT_STRATEGY, **kwargs: Any) -> PriorityStrategy:
    """Build the strategy registered under ``name``.

    ``name`` may be ``"default"`` as an alias for :data:`DEFAULT_STRATEGY`. Any
    keyword arguments are forwarded to the registered factory (typically
    ``config=`` and/or ``clock=``). Raises :class:`UnknownStrategyError` for an
    unregistered name.
    """
    resolved = DEFAULT_STRATEGY if name == "default" else name
    try:
        factory = _REGISTRY[resolved]
    except KeyError:
        raise UnknownStrategyError(name, available_strategies()) from None
    return factory(**kwargs)


register_strategy("weighted", lambda **kw: WeightedScoreStrategy(**kw))
register_strategy("sla", lambda **kw: SlaDeadlineStrategy(**kw))
