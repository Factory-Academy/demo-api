from src.utils.feature_flags import FeatureFlags


def test_is_enabled_returns_default_when_missing(monkeypatch):
    monkeypatch.delenv("FEATURE_EXPERIMENT_ALPHA", raising=False)
    flags = FeatureFlags()
    assert flags.is_enabled("experiment_alpha", default=True) is True
    assert flags.is_enabled("experiment_alpha", default=False) is False


def test_is_enabled_true_values(monkeypatch):
    monkeypatch.setenv("FEATURE_EXPERIMENT_ALPHA", "enabled")
    flags = FeatureFlags()
    assert flags.is_enabled("experiment_alpha") is True


def test_is_enabled_false_values(monkeypatch):
    monkeypatch.setenv("FEATURE_EXPERIMENT_ALPHA", "off")
    flags = FeatureFlags()
    assert flags.is_enabled("experiment_alpha", default=True) is False


def test_is_enabled_uses_default_for_unrecognized_values(monkeypatch):
    monkeypatch.setenv("FEATURE_EXPERIMENT_ALPHA", "sometimes")
    flags = FeatureFlags()
    assert flags.is_enabled("experiment_alpha", default=True) is True
    assert flags.is_enabled("experiment_alpha", default=False) is False


def test_is_enabled_normalizes_flag_name(monkeypatch):
    monkeypatch.setenv("FEATURE_WIDGETS_V2_API", "1")
    flags = FeatureFlags()
    assert flags.is_enabled("widgets-v2-api") is True
