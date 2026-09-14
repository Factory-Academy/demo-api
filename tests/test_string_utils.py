import pytest
from src.utils.string_utils import slugify

@pytest.mark.parametrize("input_str, expected", [
    ("Hello World", "hello-world"),
    ("Hello   World", "hello-world"),
    ("Hello_World", "hello-world"),
    ("  Hello World  ", "hello-world"),
    ("Hello! World?", "hello-world"),
    ("Python & FastAPI", "python-fastapi"),
    ("123", "123"),
    # Edge cases
    ("", ""),
    ("   ", ""),
    ("!!!", ""),
    ("---", ""),
    ("_-_ test _-_", "test"),
])
def test_slugify(input_str, expected):
    assert slugify(input_str) == expected
