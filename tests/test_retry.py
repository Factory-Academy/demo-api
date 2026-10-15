import pytest
from src.utils.resilience.retry import retry

def test_retry_success():
    call_count = 0
    
    @retry(tries=3)
    def succeed_immediately():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = succeed_immediately()
    assert result == "success"
    assert call_count == 1

def test_retry_eventual_success():
    call_count = 0
    
    @retry(exceptions=(ValueError,), tries=3, delay=0.01)
    def succeed_eventually():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("fail")
        return "success"
    
    result = succeed_eventually()
    assert result == "success"
    assert call_count == 2

def test_retry_failure():
    call_count = 0
    
    @retry(exceptions=(ValueError,), tries=2, delay=0.01)
    def always_fail():
        nonlocal call_count
        call_count += 1
        raise ValueError("fail")
    
    with pytest.raises(ValueError, match="fail"):
        always_fail()
    
    assert call_count == 2

def test_retry_unhandled_exception():
    call_count = 0
    
    @retry(exceptions=(ValueError,), tries=3, delay=0.01)
    def raise_unhandled():
        nonlocal call_count
        call_count += 1
        raise TypeError("unhandled")
    
    with pytest.raises(TypeError, match="unhandled"):
        raise_unhandled()
    
    assert call_count == 1
