from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    attempts: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    last_error: Exception | None = None

    for _ in range(attempts):
        try:
            return operation()
        except exceptions as exc:
            last_error = exc

    if last_error is None:
        raise RuntimeError("retry failed without capturing an exception")
    raise last_error
