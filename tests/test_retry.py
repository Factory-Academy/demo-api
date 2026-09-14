import pytest

from src.services.retry import retry


def test_retry_returns_after_eventual_success():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    assert retry(flaky, max_attempts=3) == "ok"
    assert attempts["count"] == 3


def test_retry_raises_after_max_attempts():
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise RuntimeError("still failing")

    with pytest.raises(RuntimeError, match="still failing"):
        retry(always_fails, max_attempts=2)

    assert attempts["count"] == 2


def test_retry_succeeds_on_first_attempt():
    """Edge case: function succeeds immediately."""
    attempts = {"count": 0}

    def success():
        attempts["count"] += 1
        return "immediate success"

    assert retry(success, max_attempts=1) == "immediate success"
    assert attempts["count"] == 1


def test_retry_raises_on_invalid_max_attempts_zero():
    """Edge case: max_attempts must be at least 1."""
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        retry(lambda: None, max_attempts=0)


def test_retry_raises_on_invalid_max_attempts_negative():
    """Edge case: max_attempts must be at least 1."""
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        retry(lambda: None, max_attempts=-1)
