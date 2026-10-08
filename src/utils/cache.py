from collections import OrderedDict
from functools import wraps
from time import monotonic
from typing import Any, Callable, Tuple


def ttl_cache(ttl_seconds: float, maxsize: int = 128) -> Callable:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than 0")
    if maxsize <= 0:
        raise ValueError("maxsize must be greater than 0")

    def decorator(func: Callable) -> Callable:
        cache: OrderedDict[Tuple[Any, ...], Tuple[float, Any]] = OrderedDict()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                key = (args, tuple(sorted(kwargs.items())))
                hash(key)
            except TypeError:
                return func(*args, **kwargs)

            now = monotonic()
            cached = cache.get(key)

            if cached is not None:
                expires_at, value = cached
                if expires_at > now:
                    cache.move_to_end(key)
                    return value
                del cache[key]

            result = func(*args, **kwargs)
            cache[key] = (now + ttl_seconds, result)
            cache.move_to_end(key)

            while len(cache) > maxsize:
                cache.popitem(last=False)

            return result

        def cache_clear() -> None:
            cache.clear()

        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator
