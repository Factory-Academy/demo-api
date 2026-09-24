"""Environment-driven feature flag helper."""

import os
from functools import wraps
from typing import Callable


class FeatureFlags:
    """
    Simple feature flag system driven by environment variables.

    By default, flags are checked via environment variables prefixed
    with "FEATURE_". A flag is considered enabled if its env var
    is set to "true", "1", or "yes" (case-insensitive).

    Example:
        flags.is_enabled("experimental_api")
        # Checks FEATURE_EXPERIMENTAL_API env var
    """

    def __init__(self, prefix: str = "FEATURE_"):
        """Initialize feature flags with optional custom prefix."""
        self.prefix = prefix
        self._cache = {}

    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: The flag name (case-insensitive)

        Returns:
            True if the corresponding env var is set to a truthy value
        """
        env_var = f"{self.prefix}{flag_name.upper()}"

        if env_var not in self._cache:
            value = os.getenv(env_var, "false").lower()
            self._cache[env_var] = value in ("true", "1", "yes")

        return self._cache[env_var]

    def clear_cache(self) -> None:
        """Clear the flag cache. Useful for testing."""
        self._cache.clear()

    def require_flag(self, flag_name: str) -> Callable:
        """
        Decorator to require a feature flag for a route or function.

        Returns HTTP 403 Forbidden if flag is not enabled.
        Supports both sync and async functions.

        Args:
            flag_name: The flag name to check

        Returns:
            Decorator function

        Example:
            @flags.require_flag("new_feature")
            async def my_endpoint():
                return {"status": "ok"}
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.is_enabled(flag_name):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=403,
                        detail="Feature not enabled"
                    )
                return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.is_enabled(flag_name):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=403,
                        detail="Feature not enabled"
                    )
                return func(*args, **kwargs)

            # Return the appropriate wrapper
            if hasattr(func, '__await__') or (
                hasattr(func, '__code__') and
                func.__code__.co_flags & 0x80  # CO_COROUTINE flag
            ):
                return async_wrapper
            return sync_wrapper

        return decorator


# Global instance for convenience
flags = FeatureFlags()
