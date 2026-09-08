import time
from typing import Callable, TypeVar, Any
import logging

T = TypeVar("T")
logger = logging.getLogger(__name__)

def retry(
    func: Callable[..., T],
    retries: int = 3,
    delay: float = 0.1,
    exceptions: tuple = (Exception,),
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Retry a function call multiple times.

    Args:
        func: The function to call
        retries: Number of retry attempts
        delay: Delay between retries in seconds
        exceptions: A tuple of exceptions to catch and retry
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        The result of the function call

    Raises:
        The last exception caught if all retries fail
    """
    last_exception = None
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {retries + 1} attempts failed.")
    
    if last_exception:
        raise last_exception
