import pytest

from src.services.priority import classification as clf
from src.services.priority.classification import CRITICAL, HIGH, LOW, MEDIUM


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, LOW),
        (19.9, LOW),
        (20, MEDIUM),
        (49.9, MEDIUM),
        (50, HIGH),
        (79.9, HIGH),
        (80, CRITICAL),
        (100000, CRITICAL),
    ],
)
def test_threshold_boundaries(score, expected):
    assert clf.classify_score(score) == expected


@pytest.mark.parametrize("value", [None, "nan", float("nan"), "abc", object()])
def test_non_numeric_scores_are_low(value):
    assert clf.classify_score(value) == LOW


def test_negative_score_is_low():
    assert clf.classify_score(-500) == LOW
