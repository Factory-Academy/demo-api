from src.feature_flags import FeatureFlags


def test_is_enabled_true_values():
    flags = FeatureFlags(environ={"FEATURE_ALPHA": "YES"})
    assert flags.is_enabled("alpha") is True


def test_is_enabled_false_values():
    flags = FeatureFlags(environ={"FEATURE_ALPHA": "off"})
    assert flags.is_enabled("alpha", default=True) is False


def test_is_enabled_returns_default_for_missing_or_unrecognized_values():
    flags = FeatureFlags(environ={"FEATURE_ALPHA": "maybe"})
    assert flags.is_enabled("alpha", default=False) is False
    assert flags.is_enabled("beta", default=True) is True


def test_is_enabled_accepts_prefixed_name():
    flags = FeatureFlags(environ={"FEATURE_ALPHA": "1"})
    assert flags.is_enabled("FEATURE_ALPHA") is True
