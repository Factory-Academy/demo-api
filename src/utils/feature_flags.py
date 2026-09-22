import os


TRUTHY_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSY_VALUES = {"0", "false", "no", "off", "disabled"}


class FeatureFlags:
    def __init__(self, prefix: str = "FEATURE_"):
        self.prefix = prefix

    def is_enabled(self, name: str, default: bool = False) -> bool:
        env_name = f"{self.prefix}{self._normalize_name(name)}"
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default

        normalized_value = raw_value.strip().lower()
        if normalized_value in TRUTHY_VALUES:
            return True
        if normalized_value in FALSY_VALUES:
            return False
        return default

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().replace("-", "_").upper()


feature_flags = FeatureFlags()
