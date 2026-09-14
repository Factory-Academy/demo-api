from collections import OrderedDict
from functools import wraps
from threading import RLock
from time import monotonic
from typing import Any, Callable, Tuple, TypeVar

T = TypeVar("T")
CacheKey = Tuple[Tuple[Any, ...], Tuple[Tuple[str, Any], ...]]


def ttl_cache(
    ttl_seconds: float, maxsize: int = 128
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than 0")
    if maxsize < 1:
        raise ValueError("maxsize must be at least 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: "OrderedDict[CacheKey, Tuple[T, float]]" = OrderedDict()
        lock = RLock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                key: CacheKey = (args, tuple(sorted(kwargs.items())))
                hash(key)
            except TypeError:
                return func(*args, **kwargs)

            now = monotonic()
            with lock:
                cached = cache.get(key)
                if cached is not None:
                    value, expires_at = cached
                    if expires_at > now:
                        cache.move_to_end(key)
                        return value
                    del cache[key]

                value = func(*args, **kwargs)
                cache[key] = (value, now + ttl_seconds)
                cache.move_to_end(key)

                while len(cache) > maxsize:
                    cache.popitem(last=False)

                return value

        return wrapper

    return decorator
