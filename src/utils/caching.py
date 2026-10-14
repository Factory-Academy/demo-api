import time
import threading
from functools import wraps
from collections import OrderedDict
from typing import Any, Callable, Dict, Tuple


def _make_hashable(obj: Any) -> Any:
    """Recursively convert unhashable objects into hashable ones."""
    if isinstance(obj, dict):
        return tuple((k, _make_hashable(v)) for k, v in sorted(obj.items()))
    if isinstance(obj, (list, tuple)):
        return tuple(_make_hashable(v) for v in obj)
    if isinstance(obj, (set, frozenset)):
        return tuple(_make_hashable(v) for v in sorted(list(obj)))
    return obj


def ttl_cache(ttl: int = 3600, maxsize: int = 128):
    """
    Least Recently Used (LRU) cache with Time-To-Live (TTL).
    
    Args:
        ttl: Time to live in seconds. Must be >= 0.
        maxsize: Maximum number of items in the cache. Must be >= 0.
    """
    if ttl < 0:
        raise ValueError("TTL must be non-negative")
    if maxsize < 0:
        raise ValueError("maxsize must be non-negative")

    def decorator(func: Callable):
        cache: Dict[Any, Tuple[Any, float]] = OrderedDict()
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            if maxsize == 0:
                return func(*args, **kwargs)

            # Create a hashable key from args and kwargs
            key = _make_hashable((args, kwargs))
            now = time.time()

            with lock:
                if key in cache:
                    result, timestamp = cache[key]
                    if now - timestamp < ttl:
                        # Move to end to maintain LRU property
                        cache.move_to_end(key)
                        return result
                    else:
                        del cache[key]

            result = func(*args, **kwargs)

            # Only cache if ttl > 0. If ttl is 0, we could still cache it for 
            # the duration of the current 'now', but practically it's useless.
            # However, standard behavior for ttl=0 might be "no cache".
            if ttl > 0:
                with lock:
                    cache[key] = (result, now)
                    if len(cache) > maxsize:
                        # Remove the oldest item (first in OrderedDict)
                        cache.popitem(last=False)

            return result

        def cache_clear():
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore
        return wrapper

    return decorator
