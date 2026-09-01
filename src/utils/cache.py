import inspect
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional


def _make_cache_key(args: tuple, kwargs: dict) -> Optional[tuple]:
    key = (args, tuple(sorted(kwargs.items())))
    try:
        hash(key)
    except TypeError:
        return None
    return key


def ttl_cache(ttl_seconds: float, maxsize: int = 128) -> Callable:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than 0")
    if maxsize <= 0:
        raise ValueError("maxsize must be greater than 0")

    def decorator(func: Callable) -> Callable:
        cache: OrderedDict = OrderedDict()

        def _read_from_cache(cache_key: tuple) -> tuple[bool, Any]:
            now = time.monotonic()
            cached = cache.get(cache_key)
            if cached is None:
                return False, None

            expires_at, value = cached
            if now >= expires_at:
                cache.pop(cache_key, None)
                return False, None

            cache.move_to_end(cache_key)
            return True, value

        def _write_to_cache(cache_key: tuple, value: Any) -> None:
            cache[cache_key] = (time.monotonic() + ttl_seconds, value)
            cache.move_to_end(cache_key)
            if len(cache) > maxsize:
                cache.popitem(last=False)

        def _cache_clear() -> None:
            cache.clear()

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_key = _make_cache_key(args, kwargs)
                if cache_key is None:
                    return await func(*args, **kwargs)

                found, value = _read_from_cache(cache_key)
                if found:
                    return value

                value = await func(*args, **kwargs)
                _write_to_cache(cache_key, value)
                return value

            async_wrapper.cache_clear = _cache_clear
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = _make_cache_key(args, kwargs)
            if cache_key is None:
                return func(*args, **kwargs)

            found, value = _read_from_cache(cache_key)
            if found:
                return value

            value = func(*args, **kwargs)
            _write_to_cache(cache_key, value)
            return value

        sync_wrapper.cache_clear = _cache_clear
        return sync_wrapper

    return decorator


def retry(
    attempts: int = 3,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    delay_seconds: float = 0.0,
) -> Callable:
    if attempts <= 0:
        raise ValueError("attempts must be greater than 0")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be greater than or equal to 0")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == attempts - 1:
                        raise
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)

        return wrapper

    return decorator
