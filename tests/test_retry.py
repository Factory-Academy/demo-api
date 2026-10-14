from src.services.retry import retry


def test_retry_succeeds_after_transient_error():
    attempts = {"count": 0}

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("temporary failure")
        return "ok"

    result = retry(flaky_operation, retries=1, retry_on=(ValueError,))

    assert result == "ok"
    assert attempts["count"] == 2
