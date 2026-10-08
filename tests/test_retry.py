import pytest
from src.utils.resilience.retry import retry


def test_retry_succeeds_on_first_attempt():
    call_count = 0

    @retry(max_attempts=3)
    def succeeds_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = succeeds_immediately()
    assert result == "success"
    assert call_count == 1


def test_retry_succeeds_after_failures():
    call_count = 0

    @retry(max_attempts=3, delay=0.01)
    def succeeds_on_third_attempt():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("temporary failure")
        return "success"

    result = succeeds_on_third_attempt()
    assert result == "success"
    assert call_count == 3


def test_retry_exhausts_attempts():
    call_count = 0

    @retry(max_attempts=3, delay=0.01)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("permanent failure")

    with pytest.raises(ValueError, match="permanent failure"):
        always_fails()

    assert call_count == 3


def test_retry_with_specific_exception():
    call_count = 0

    @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
    def fails_with_type_error():
        nonlocal call_count
        call_count += 1
        raise TypeError("not retryable")

    with pytest.raises(TypeError, match="not retryable"):
        fails_with_type_error()

    assert call_count == 1
