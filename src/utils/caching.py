import time
from functools import wraps
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple


def _make_hashable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))
    if isinstance(obj, list):
        return tuple(_make_hashable(v) for v in obj)
    if isinstance(obj, tuple):
        return tuple(_make_hashable(v) for v in obj)
    if isinstance(obj, (set, frozenset)):
        return tuple(_make_hashable(v) for v in sorted(list(obj)))
    return obj


def ttl_cache(ttl: int = 3600, maxsize: int = 128):
    """
    Least Recently Used (LRU) cache with Time-To-Live (TTL).
    
    Args:
        ttl: Time to live in seconds.
        maxsize: Maximum number of items in the cache.
    """
    def decorator(func: Callable):
        cache: Dict[Any, Tuple[Any, float]] = OrderedDict()

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a hashable key from args and kwargs
            key = _make_hashable((args, kwargs))
            now = time.time()

            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl:
                    # Move to end to maintain LRU property
                    if hasattr(cache, "move_to_end"):
                        cache.move_to_end(key)
                    return result
                else:
                    del cache[key]

            result = func(*args, **kwargs)
            cache[key] = (result, now)

            if len(cache) > maxsize:
                # Remove the oldest item (first in OrderedDict)
                if hasattr(cache, "popitem"):
                    cache.popitem(last=False)
                else:
                    # Fallback for very old python versions if needed, 
                    # but OrderedDict is standard since 3.7+ (maintained order)
                    first_key = next(iter(cache))
                    del cache[first_key]

            return result

        def cache_clear():
            cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore
        return wrapper

    return decorator
