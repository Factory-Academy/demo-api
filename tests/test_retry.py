import pytest
from src.utils.retry import retry

def test_retry_success():
    def succeed():
        return "success"
    
    assert retry(succeed) == "success"

def test_retry_eventual_success():
    attempts = 0
    def succeed_on_third():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Fail")
        return "success"
    
    # retries=2 means 3 attempts total (1 original + 2 retries)
    assert retry(succeed_on_third, retries=2, delay=0.01) == "success"
    assert attempts == 3

def test_retry_failure():
    def fail():
        raise ValueError("Permanent failure")
    
    with pytest.raises(ValueError, match="Permanent failure"):
        retry(fail, retries=2, delay=0.01)

def test_retry_specific_exception():
    attempts = 0
    def fail_with_type_error():
        nonlocal attempts
        attempts += 1
        raise TypeError("Unexpected")

    # Should not retry for TypeError if we only specify ValueError
    with pytest.raises(TypeError, match="Unexpected"):
        retry(fail_with_type_error, retries=2, delay=0.01, exceptions=(ValueError,))
    
    assert attempts == 1

def test_retry_with_args():
    def add(a, b):
        return a + b
    
    assert retry(add, 2, 0.01, (Exception,), 1, 2) == 3
    assert retry(add, 2, 0.01, (Exception,), a=5, b=10) == 15
