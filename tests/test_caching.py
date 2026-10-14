import time
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
