"""Exceptions for the cache utility."""

class CacheError(Exception):
    """Base class for cache errors."""
    pass

class CacheMissError(CacheError):
    """Raised when a key is not found in the cache."""
    pass
