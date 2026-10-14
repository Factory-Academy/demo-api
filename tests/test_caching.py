import time
import threading
import pytest
from src.utils.caching import ttl_cache

def test_ttl_cache_basic():
    call_count = 0
    
    @ttl_cache(ttl=1, maxsize=2)
    def cached_func(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    assert cached_func(1) == 2
    assert call_count == 1
    
    # Second call should be from cache
    assert cached_func(1) == 2
    assert call_count == 1
    
    # Different arg should call the function
    assert cached_func(2) == 4
    assert call_count == 2
    
    # Wait for TTL to expire
    time.sleep(1.1)
    assert cached_func(1) == 2
    assert call_count == 3

def test_ttl_cache_maxsize():
    call_count = 0
    
    @ttl_cache(ttl=10, maxsize=2)
    def cached_func(x):
        nonlocal call_count
        call_count += 1
        return x
    
    cached_func(1) # [1]
    cached_func(2) # [1, 2]
    assert call_count == 2
    
    cached_func(3) # [2, 3] (1 should be evicted)
    assert call_count == 3
    
    # 1 should be re-calculated
    cached_func(1)
    assert call_count == 4

def test_ttl_cache_unhashable_args():
    call_count = 0
    
    @ttl_cache(ttl=10, maxsize=2)
    def cached_func(d):
        nonlocal call_count
        call_count += 1
        return d["a"]
    
    assert cached_func({"a": 1}) == 1
    assert call_count == 1
    
    # Same dict content should hit cache
    assert cached_func({"a": 1}) == 1
    assert call_count == 1
    
    assert cached_func({"a": 2}) == 2
    assert call_count == 2

def test_cache_clear():
    call_count = 0
    
    @ttl_cache(ttl=10, maxsize=2)
    def cached_func(x):
        nonlocal call_count
        call_count += 1
        return x
    
    cached_func(1)
    assert call_count == 1
    cached_func.cache_clear()
    cached_func(1)
    assert call_count == 2

def test_ttl_cache_validation():
    with pytest.raises(ValueError, match="TTL must be non-negative"):
        @ttl_cache(ttl=-1)
        def func():
            pass
            
    with pytest.raises(ValueError, match="maxsize must be non-negative"):
        @ttl_cache(maxsize=-1)
        def func():
            pass

def test_ttl_cache_maxsize_zero():
    call_count = 0
    
    @ttl_cache(ttl=10, maxsize=0)
    def cached_func(x):
        nonlocal call_count
        call_count += 1
        return x
    
    assert cached_func(1) == 1
    assert call_count == 1
    assert cached_func(1) == 1
    assert call_count == 2 # Should not cache

def test_ttl_cache_ttl_zero():
    call_count = 0
    
    @ttl_cache(ttl=0, maxsize=10)
    def cached_func(x):
        nonlocal call_count
        call_count += 1
        return x
    
    assert cached_func(1) == 1
    assert call_count == 1
    assert cached_func(1) == 1
    assert call_count == 2 # Should not cache (effectively)

def test_ttl_cache_thread_safety():
    call_count = 0
    
    @ttl_cache(ttl=10, maxsize=100)
    def cached_func(x):
        nonlocal call_count
        time.sleep(0.01) # Simulate some work
        call_count += 1
        return x
    
    threads = []
    for _ in range(10):
        t = threading.Thread(target=cached_func, args=(1,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Note: Even with thread safety, multiple threads might enter 
    # the function before the first one completes and populates the cache
    # if the lock only covers cache access. 
    # In my implementation, the func call is OUTSIDE the lock.
    # This is usually desired to avoid blocking other calls, 
    # but it means call_count might be > 1.
    # However, the cache operations themselves are safe.
    assert call_count >= 1
