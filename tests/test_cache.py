import time
import pytest
from src.utils.cache import cached, TTLCache


def test_ttl_cache_basic_operations():
    cache = TTLCache(ttl=60.0, maxsize=10)
    
    # Set and get
    cache.set(("key1",), "value1")
    assert cache.get(("key1",)) == "value1"
    
    # Non-existent key
    assert cache.get(("nonexistent",)) is None
    
    # Length
    assert len(cache) == 1


def test_ttl_cache_expiration():
    cache = TTLCache(ttl=0.1, maxsize=10)
    
    cache.set(("key1",), "value1")
    assert cache.get(("key1",)) == "value1"
    
    # Wait for expiration
    time.sleep(0.15)
    assert cache.get(("key1",)) is None
    assert len(cache) == 0


def test_ttl_cache_maxsize_eviction():
    cache = TTLCache(ttl=60.0, maxsize=3)
    
    cache.set(("key1",), "value1")
    cache.set(("key2",), "value2")
    cache.set(("key3",), "value3")
    assert len(cache) == 3
    
    # Adding fourth item should evict oldest (key1)
    cache.set(("key4",), "value4")
    assert len(cache) == 3
    assert cache.get(("key1",)) is None
    assert cache.get(("key2",)) == "value2"
    assert cache.get(("key3",)) == "value3"
    assert cache.get(("key4",)) == "value4"


def test_ttl_cache_lru_ordering():
    cache = TTLCache(ttl=60.0, maxsize=3)
    
    cache.set(("key1",), "value1")
    cache.set(("key2",), "value2")
    cache.set(("key3",), "value3")
    
    # Access key1 to move it to end (most recently used)
    cache.get(("key1",))
    
    # Adding key4 should evict key2 (now oldest)
    cache.set(("key4",), "value4")
    assert cache.get(("key1",)) == "value1"
    assert cache.get(("key2",)) is None
    assert cache.get(("key3",)) == "value3"
    assert cache.get(("key4",)) == "value4"


def test_ttl_cache_update_existing():
    cache = TTLCache(ttl=60.0, maxsize=10)
    
    cache.set(("key1",), "value1")
    cache.set(("key1",), "value2")
    
    assert cache.get(("key1",)) == "value2"
    assert len(cache) == 1


def test_ttl_cache_clear():
    cache = TTLCache(ttl=60.0, maxsize=10)
    
    cache.set(("key1",), "value1")
    cache.set(("key2",), "value2")
    assert len(cache) == 2
    
    cache.clear()
    assert len(cache) == 0
    assert cache.get(("key1",)) is None


def test_cached_decorator_basic():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def add(x, y):
        nonlocal call_count
        call_count += 1
        return x + y
    
    # First call - should execute function
    result1 = add(1, 2)
    assert result1 == 3
    assert call_count == 1
    
    # Second call with same args - should use cache
    result2 = add(1, 2)
    assert result2 == 3
    assert call_count == 1
    
    # Different args - should execute function
    result3 = add(2, 3)
    assert result3 == 5
    assert call_count == 2


def test_cached_decorator_with_kwargs():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def greet(name, greeting="Hello"):
        nonlocal call_count
        call_count += 1
        return f"{greeting}, {name}!"
    
    # First call
    result1 = greet("Alice", greeting="Hi")
    assert result1 == "Hi, Alice!"
    assert call_count == 1
    
    # Same call - should use cache
    result2 = greet("Alice", greeting="Hi")
    assert result2 == "Hi, Alice!"
    assert call_count == 1
    
    # Different kwargs
    result3 = greet("Alice", greeting="Hello")
    assert result3 == "Hello, Alice!"
    assert call_count == 2


def test_cached_decorator_ttl_expiration():
    call_count = 0
    
    @cached(ttl=0.1, maxsize=10)
    def compute(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # First call
    result1 = compute(5)
    assert result1 == 10
    assert call_count == 1
    
    # Cached call
    result2 = compute(5)
    assert result2 == 10
    assert call_count == 1
    
    # Wait for expiration
    time.sleep(0.15)
    
    # Should execute function again
    result3 = compute(5)
    assert result3 == 10
    assert call_count == 2


def test_cached_decorator_maxsize():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=2)
    def square(x):
        nonlocal call_count
        call_count += 1
        return x * x
    
    # Fill cache
    square(1)  # call_count = 1
    square(2)  # call_count = 2
    assert call_count == 2
    
    # Should use cache
    square(1)
    square(2)
    assert call_count == 2
    
    # Adding third item should evict oldest
    square(3)  # call_count = 3
    assert call_count == 3
    
    # First item should be evicted, need to recompute
    square(1)  # call_count = 4
    assert call_count == 4


def test_cached_decorator_cache_exposure():
    @cached(ttl=60.0, maxsize=10)
    def example(x):
        return x + 1
    
    # Cache should be exposed for inspection
    assert hasattr(example, 'cache')
    assert isinstance(example.cache, TTLCache)
    
    # Should start empty
    assert len(example.cache) == 0
    
    # After call, should have one entry
    example(5)
    assert len(example.cache) == 1
    
    # Clear should work
    example.cache.clear()
    assert len(example.cache) == 0


def test_cached_decorator_with_none_return():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def may_return_none(x):
        nonlocal call_count
        call_count += 1
        return None if x == 0 else x
    
    # First call returning None
    result1 = may_return_none(0)
    assert result1 is None
    assert call_count == 1
    
    # Note: Current implementation doesn't cache None values
    # This is intentional to distinguish from cache miss
    result2 = may_return_none(0)
    assert result2 is None
    assert call_count == 2
    
    # Non-None values should cache
    result3 = may_return_none(5)
    assert result3 == 5
    assert call_count == 3
    
    result4 = may_return_none(5)
    assert result4 == 5
    assert call_count == 3


def test_cached_decorator_different_types():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def process(data):
        nonlocal call_count
        call_count += 1
        return str(data)
    
    # String
    process("test")
    # Tuple
    process((1, 2, 3))
    # Int
    process(42)
    
    assert call_count == 3
    
    # Should use cache
    process("test")
    process((1, 2, 3))
    process(42)
    
    assert call_count == 3


def test_cached_decorator_with_dict_args():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def process_dict(data):
        nonlocal call_count
        call_count += 1
        return data.get("value", 0) * 2
    
    # First call with dict
    result1 = process_dict({"value": 5})
    assert result1 == 10
    assert call_count == 1
    
    # Same dict - should use cache
    result2 = process_dict({"value": 5})
    assert result2 == 10
    assert call_count == 1
    
    # Different dict
    result3 = process_dict({"value": 10})
    assert result3 == 20
    assert call_count == 2


def test_cached_decorator_with_nested_dict():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def process_nested(data):
        nonlocal call_count
        call_count += 1
        return data["nested"]["value"]
    
    # First call
    result1 = process_nested({"nested": {"value": 42}})
    assert result1 == 42
    assert call_count == 1
    
    # Same nested dict - should use cache
    result2 = process_nested({"nested": {"value": 42}})
    assert result2 == 42
    assert call_count == 1


def test_cached_decorator_with_list_args():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def sum_list(items):
        nonlocal call_count
        call_count += 1
        return sum(items)
    
    # First call
    result1 = sum_list([1, 2, 3])
    assert result1 == 6
    assert call_count == 1
    
    # Same list - should use cache
    result2 = sum_list([1, 2, 3])
    assert result2 == 6
    assert call_count == 1
    
    # Different list
    result3 = sum_list([4, 5, 6])
    assert result3 == 15
    assert call_count == 2


def test_cached_decorator_dict_key_order_independence():
    call_count = 0
    
    @cached(ttl=60.0, maxsize=10)
    def process_dict(data):
        nonlocal call_count
        call_count += 1
        return data.get("a", 0) + data.get("b", 0)
    
    # Call with one key order
    result1 = process_dict({"a": 1, "b": 2})
    assert result1 == 3
    assert call_count == 1
    
    # Call with different key order - should still use cache
    result2 = process_dict({"b": 2, "a": 1})
    assert result2 == 3
    assert call_count == 1
