import time
from functools import wraps
from typing import Any, Callable, Optional


def _make_hashable(obj: Any) -> Any:
    """Convert unhashable types to hashable equivalents."""
    if isinstance(obj, dict):
        return frozenset((k, _make_hashable(v)) for k, v in obj.items())
    elif isinstance(obj, list):
        return tuple(_make_hashable(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(_make_hashable(item) for item in obj)
    return obj


def cached(ttl: int = 300, maxsize: int = 128) -> Callable:
    """
    Caching decorator with TTL (time-to-live) and maxsize support.

    Args:
        ttl: Time-to-live in seconds. Cached values expire after this duration.
        maxsize: Maximum number of cached items. When exceeded, oldest items are removed.

    Returns:
        A decorator function that caches function results.

    Example:
        @cached(ttl=300, maxsize=64)
        def expensive_operation(x):
            return x ** 2
    """

    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_order = []

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a hashable cache key from arguments
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = tuple(sorted((k, _make_hashable(v)) for k, v in kwargs.items()))
            cache_key = (hashable_args, hashable_kwargs)

            # Check if key is in cache and not expired
            if cache_key in cache:
                cached_value, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return cached_value
                else:
                    # Expired, remove from cache
                    del cache[cache_key]
                    cache_order.remove(cache_key)

            # Call the function and cache the result
            result = func(*args, **kwargs)
            current_time = time.time()
            cache[cache_key] = (result, current_time)
            cache_order.append(cache_key)

            # Enforce maxsize by removing oldest entries
            while len(cache) > maxsize:
                oldest_key = cache_order.pop(0)
                del cache[oldest_key]

            return result

        return wrapper

    return decorator
