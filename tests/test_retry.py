from src.retry import retry


def test_retry_retries_until_operation_succeeds():
    attempts = {"count": 0}

    def flaky_operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("temporary failure")
        return "ok"

    result = retry(flaky_operation, attempts=3, exceptions=(ValueError,))

    assert result == "ok"
    assert attempts["count"] == 3
