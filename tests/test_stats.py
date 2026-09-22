from src.utils.stats import success_rate


def test_success_rate_returns_zero_when_total_is_zero():
    assert success_rate(3, 0) == 0.0
