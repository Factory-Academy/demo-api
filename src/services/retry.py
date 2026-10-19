from typing import Callable, TypeVar


T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    retries: int = 1,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> T:
    for attempt in range(retries + 1):
        try:
            return operation()
        except retry_on as error:
            if attempt == retries:
                raise error
            if on_retry is not None:
                on_retry(error, attempt + 1)
