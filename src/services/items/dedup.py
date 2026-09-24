"""Order-preserving de-duplication that tolerates unhashable elements.

Extracted from :func:`batch.normalize_ids`, whose original de-dup used a plain
``set``. That raised ``TypeError`` the moment a caller passed an unhashable
identifier (for example a ``list`` or ``dict`` id from a composite key), which
is exactly the kind of malformed-input edge case the surrounding module is
meant to absorb rather than crash on. Keeping the logic here makes it a small,
pure, independently testable unit.
"""

from typing import Any, Iterable, Iterator, List


def dedupe_preserving_order(items: Iterable[Any]) -> Iterator[Any]:
    """Yield each element once, in first-seen order, without raising.

    Hashable elements are tracked in a ``set`` for O(1) membership. Unhashable
    elements (which cannot go in a set) fall back to a linear scan of an
    already-seen list, so de-duplication degrades in cost but never blows up on
    a ``list``/``dict`` identifier. Equal-but-unhashable values are still
    collapsed to a single occurrence.
    """
    seen_hashable = set()
    seen_unhashable: List[Any] = []
    for item in items:
        try:
            if item in seen_hashable:
                continue
            seen_hashable.add(item)
        except TypeError:
            # Unhashable: `in`/`add` against the set raised before mutating it.
            if item in seen_unhashable:
                continue
            seen_unhashable.append(item)
        yield item
