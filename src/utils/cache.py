from collections import OrderedDict
from functools import wraps
from threading import RLock
from time import monotonic
from typing import Any, Callable, Tuple, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
_KW_MARKER = object()


def _make_key(args: tuple, kwargs: dict) -> Tuple[Any, ...]:
    if not kwargs:
        return args
    return args + (_KW_MARKER,) + tuple(sorted(kwargs.items()))


def ttl_cache(
    ttl_seconds: float,
    maxsize: int = 128,
    time_func: Callable[[], float] = monotonic,
) -> Callable[[F], F]:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than 0")
    if maxsize < 1:
        raise ValueError("maxsize must be at least 1")

    def decorator(func: F) -> F:
        cache = OrderedDict()
        lock = RLock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                key = _make_key(args, kwargs)
                hash(key)
            except TypeError:
                return func(*args, **kwargs)

            now = time_func()
            with lock:
                entry = cache.get(key)
                if entry is not None:
                    value, expires_at = entry
                    if now < expires_at:
                        cache.move_to_end(key)
                        return value
                    del cache[key]

            value = func(*args, **kwargs)
            with lock:
                cache[key] = (value, now + ttl_seconds)
                cache.move_to_end(key)
                while len(cache) > maxsize:
                    cache.popitem(last=False)

            return value

        def cache_clear() -> None:
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
