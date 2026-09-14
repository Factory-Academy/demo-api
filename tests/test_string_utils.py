import pytest

import src.utils.string_utils as string_utils
from src.utils.string_utils import slugify


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("Hello World", "hello-world"),
        ("Hello   World", "hello-world"),
        ("Hello_World", "hello-world"),
        ("  Hello World  ", "hello-world"),
        ("Hello! World?", "hello-world"),
        ("Python & FastAPI", "python-fastapi"),
        ("123", "123"),
    ],
)
def test_slugify(input_str, expected):
    assert slugify(input_str) == expected


def test_slugify_uses_cache_for_repeated_values(monkeypatch):
    original_sub = string_utils.re.sub
    call_count = {"count": 0}

    def counting_sub(pattern, repl, text):
        call_count["count"] += 1
        return original_sub(pattern, repl, text)

    monkeypatch.setattr(string_utils.re, "sub", counting_sub)

    assert slugify("Caching Test") == "caching-test"
    assert slugify("Caching Test") == "caching-test"
    assert call_count["count"] == 2
