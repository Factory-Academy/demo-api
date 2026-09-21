"""
Caching utilities with TTL and maxsize support.
"""
from functools import wraps
from time import time
from typing import Optional, Callable, Any, Hashable
from collections import OrderedDict
import json


class TTLCache:
    """
    A time-to-live cache with maximum size limit.
    
    Args:
        ttl: Time-to-live in seconds for cache entries
        maxsize: Maximum number of entries in the cache
    """
    
    def __init__(self, ttl: float, maxsize: int):
        self.ttl = ttl
        self.maxsize = maxsize
        self._cache: OrderedDict[tuple, tuple[Any, float]] = OrderedDict()
    
    def get(self, key: tuple) -> Optional[Any]:
        """Get a value from cache if it exists and hasn't expired."""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        if time() - timestamp > self.ttl:
            # Entry expired, remove it
            del self._cache[key]
            return None
        
        # Move to end to mark as recently used (LRU)
        self._cache.move_to_end(key)
        return value
    
    def set(self, key: tuple, value: Any) -> None:
        """Set a value in cache, evicting oldest entry if at maxsize."""
        # If key already exists, update it
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = (value, time())
            return
        
        # If at maxsize, evict oldest (first) entry
        if len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)
        
        self._cache[key] = (value, time())
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
    
    def __len__(self) -> int:
        """Return the number of entries in the cache."""
        return len(self._cache)


def _make_hashable(obj: Any) -> Hashable:
    """
    Convert an object to a hashable type for use as a cache key.
    
    Args:
        obj: Object to convert
    
    Returns:
        Hashable representation of the object
    """
    if isinstance(obj, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, (list, tuple)):
        return tuple(_make_hashable(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(_make_hashable(item) for item in obj)
    else:
        # Attempt to use the object as-is; if unhashable, fall back to JSON
        try:
            hash(obj)
            return obj
        except TypeError:
            return json.dumps(obj, sort_keys=True, default=str)


def cached(ttl: float = 60.0, maxsize: int = 128) -> Callable:
    """
    Decorator to cache function results with TTL and maxsize limits.
    
    Args:
        ttl: Time-to-live in seconds (default: 60)
        maxsize: Maximum cache entries (default: 128)
    
    Returns:
        Decorated function with caching
    
    Example:
        @cached(ttl=30.0, maxsize=100)
        def expensive_function(x, y):
            return x + y
    """
    def decorator(func: Callable) -> Callable:
        cache = TTLCache(ttl=ttl, maxsize=maxsize)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            hashable_args = tuple(_make_hashable(arg) for arg in args)
            hashable_kwargs = tuple(
                sorted((k, _make_hashable(v)) for k, v in kwargs.items())
            )
            key = (hashable_args, hashable_kwargs)
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache the result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        # Expose cache for testing/inspection
        wrapper.cache = cache
        return wrapper
    
    return decorator
