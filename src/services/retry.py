from typing import Callable, TypeVar

T = TypeVar("T")


def retry(
    func: Callable[[], T],
    max_attempts: int = 3,
    *,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if not retry_exceptions:
        raise ValueError("retry_exceptions must contain at least one exception type")

    last_error = None
    for _ in range(max_attempts):
        try:
            return func()
        except retry_exceptions as error:
            last_error = error

    raise last_error
