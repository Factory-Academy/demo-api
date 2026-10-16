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


def test_retry_raises_after_exhausting_retries():
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise ValueError("still failing")

    try:
        retry(always_fails, retries=1, retry_on=(ValueError,))
    except ValueError as error:
        assert str(error) == "still failing"
    else:
        assert False, "Expected ValueError to be raised"

    assert attempts["count"] == 2
