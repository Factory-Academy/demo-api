import pytest
from src.utils.string_utils import slugify
from src.utils.string_utils import to_title_case

@pytest.mark.parametrize("input_str, expected", [
    ("Hello World", "hello-world"),
    ("Hello   World", "hello-world"),
    ("Hello_World", "hello-world"),
    ("  Hello World  ", "hello-world"),
    ("Hello! World?", "hello-world"),
    ("Python & FastAPI", "python-fastapi"),
    ("123", "123"),
    (None, ""),
])
def test_slugify(input_str, expected):
    assert slugify(input_str) == expected


@pytest.mark.parametrize("input_str, expected", [
    ("hello world", "Hello World"),
    ("  hello   world  ", "Hello World"),
    ("python fastapi", "Python Fastapi"),
    ("MIXED case INPUT", "Mixed Case Input"),
    (None, ""),
])
def test_to_title_case(input_str, expected):
    assert to_title_case(input_str) == expected
