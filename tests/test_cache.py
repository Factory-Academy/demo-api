import time
from src.utils.cache import cached


def test_cached_returns_same_value():
    """Test that cached decorator returns the same value for identical arguments."""
    call_count = 0

    @cached(ttl=300, maxsize=128)
    def add(a, b):
        nonlocal call_count
        call_count += 1
        return a + b

    result1 = add(2, 3)
    result2 = add(2, 3)

    assert result1 == 5
    assert result2 == 5
    assert call_count == 1  # Function should only be called once


def test_cached_different_arguments():
    """Test that cached decorator calls function for different arguments."""
    call_count = 0

    @cached(ttl=300, maxsize=128)
    def multiply(a, b):
        nonlocal call_count
        call_count += 1
        return a * b

    result1 = multiply(2, 3)
    result2 = multiply(3, 4)
    result3 = multiply(2, 3)

    assert result1 == 6
    assert result2 == 12
    assert result3 == 6
    assert call_count == 2  # Function called twice (different args on second call)


def test_cached_ttl_expiration():
    """Test that cached values expire after TTL."""
    call_count = 0

    @cached(ttl=1, maxsize=128)
    def expensive_func(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive_func(5)
    assert result1 == 10
    assert call_count == 1

    # Call again immediately (within TTL)
    result2 = expensive_func(5)
    assert result2 == 10
    assert call_count == 1  # Should still be 1

    # Wait for TTL to expire
    time.sleep(1.1)

    # Call again after TTL expiration
    result3 = expensive_func(5)
    assert result3 == 10
    assert call_count == 2  # Should be called again


def test_cached_maxsize_eviction():
    """Test that oldest items are evicted when maxsize is exceeded (FIFO order)."""
    call_count = 0

    @cached(ttl=300, maxsize=3)
    def identity(x):
        nonlocal call_count
        call_count += 1
        return x

    # Fill cache to maxsize: adds 1, 2, 3
    identity(1)
    identity(2)
    identity(3)
    assert call_count == 3

    # Call each again (should be cached, order is still 1, 2, 3)
    identity(1)
    identity(2)
    identity(3)
    assert call_count == 3

    # Add one more item (should evict oldest, which is 1)
    # Cache: [2, 3, 4]
    identity(4)
    assert call_count == 4

    # Verify 1 is no longer cached (gets recomputed)
    identity(1)
    assert call_count == 5
    # Cache is now: [3, 4, 1]

    # Verify 2 is no longer cached (was evicted when 1 was re-added)
    identity(2)
    assert call_count == 6
    # Cache is now: [4, 1, 2]


def test_cached_with_kwargs():
    """Test that cached decorator works with keyword arguments."""
    call_count = 0

    @cached(ttl=300, maxsize=128)
    def greet(name, greeting="Hello"):
        nonlocal call_count
        call_count += 1
        return f"{greeting}, {name}!"

    result1 = greet("Alice", greeting="Hi")
    result2 = greet("Alice", greeting="Hi")
    result3 = greet("Alice", greeting="Hey")

    assert result1 == "Hi, Alice!"
    assert result2 == "Hi, Alice!"
    assert result3 == "Hey, Alice!"
    assert call_count == 2  # Two different argument combinations


def test_cached_decorator_preserves_function_name():
    """Test that decorator preserves function metadata."""

    @cached(ttl=300, maxsize=128)
    def my_function():
        """This is my function."""
        return 42

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "This is my function."


def test_cached_with_none_values():
    """Test that caching works with None values in arguments."""
    call_count = 0

    @cached(ttl=300, maxsize=128)
    def func_with_none(a, b=None):
        nonlocal call_count
        call_count += 1
        return (a, b)

    result1 = func_with_none(1, None)
    result2 = func_with_none(1, None)

    assert result1 == (1, None)
    assert result2 == (1, None)
    assert call_count == 1  # Should be cached
