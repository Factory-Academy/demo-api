from typing import Callable, TypeVar

T = TypeVar("T")


def retry(func: Callable[[], T], max_attempts: int = 3) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_error = None
    for _ in range(max_attempts):
        try:
            return func()
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise last_error
