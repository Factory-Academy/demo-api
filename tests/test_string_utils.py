import pytest
from src.utils.string_utils import slugify

@pytest.mark.parametrize("input_str, expected", [
    ("Hello World", "hello-world"),
    ("Hello   World", "hello-world"),
    ("Hello_World", "hello_world"),
    ("  Hello World  ", "hello-world"),
    ("héllo wörld", "hello-world"),
    ("Hello! World?", "hello-world"),
    ("123", "123"),
    ("", ""),
])
def test_slugify(input_str, expected):
    assert slugify(input_str) == expected
