import time
import functools
import logging
from typing import Type, Tuple, Callable, Any

logger = logging.getLogger(__name__)

def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    tries: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
) -> Callable:
    """
    A tiny retry decorator.
    
    Args:
        exceptions: A tuple of exceptions to catch.
        tries: Total number of attempts.
        delay: Initial delay between attempts in seconds.
        backoff: Multiplier applied to delay after each attempt.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Retrying {func.__name__} due to {e}. {mtries-1} attempts left.")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator
