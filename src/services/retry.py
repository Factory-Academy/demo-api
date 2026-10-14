from typing import Callable, TypeVar


T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    retries: int = 1,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    attempts = retries + 1
    last_error: Exception | None = None

    for _ in range(attempts):
        try:
            return operation()
        except retry_on as error:
            last_error = error

    if last_error is not None:
        raise last_error

    raise RuntimeError("Retry failed without capturing an error")
