import os
from typing import Mapping, Optional


class FeatureFlags:
    """Environment-driven feature flag helper."""

    TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
    FALSE_VALUES = {"0", "false", "no", "off", "disabled"}

    def __init__(
        self,
        environ: Optional[Mapping[str, str]] = None,
        prefix: str = "FEATURE_",
    ) -> None:
        self.environ = environ if environ is not None else os.environ
        self.prefix = prefix

    def is_enabled(self, name: str, default: bool = False) -> bool:
        key = self._to_env_key(name)
        raw_value = self.environ.get(key)
        if raw_value is None:
            return default

        normalized = raw_value.strip().lower()
        if normalized in self.TRUE_VALUES:
            return True
        if normalized in self.FALSE_VALUES:
            return False
        return default

    def _to_env_key(self, name: str) -> str:
        normalized_name = name.strip().upper()
        if normalized_name.startswith(self.prefix):
            return normalized_name
        return f"{self.prefix}{normalized_name}"


feature_flags = FeatureFlags()


def is_feature_enabled(name: str, default: bool = False) -> bool:
    return feature_flags.is_enabled(name=name, default=default)
