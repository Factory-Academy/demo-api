"""Simple retry decorator for transient failures."""
import time
from functools import wraps
from typing import Callable, Type, TypeVar

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry a function on failure.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay: Delay between retries in seconds (default: 0.1)
        exceptions: Tuple of exception types to catch (default: (Exception,))

    Returns:
        Decorated function that retries on failure
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise last_exception

        return wrapper

    return decorator
