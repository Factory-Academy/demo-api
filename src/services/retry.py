from typing import Callable, TypeVar


T = TypeVar("T")


def retry(
    operation: Callable[[], T],
    retries: int = 1,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    for attempt in range(retries + 1):
        try:
            return operation()
        except retry_on as error:
            if attempt == retries:
                raise error
