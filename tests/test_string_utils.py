import pytest
from src.utils.string_utils import normalize_whitespace, slugify

@pytest.mark.parametrize("input_str, expected", [
    ("Hello World", "hello-world"),
    ("Hello   World", "hello-world"),
    ("Hello_World", "hello-world"),
    ("  Hello World  ", "hello-world"),
    ("Hello! World?", "hello-world"),
    ("Python & FastAPI", "python-fastapi"),
    ("123", "123"),
])
def test_slugify(input_str, expected):
    assert slugify(input_str) == expected


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("hello", "hello"),
        ("  hello   world  ", "hello world"),
        ("hello\t\tworld\nagain", "hello world again"),
        ("", ""),
    ],
)
def test_normalize_whitespace(input_str, expected):
    assert normalize_whitespace(input_str) == expected
