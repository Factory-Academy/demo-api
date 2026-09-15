import pytest
from src.utils import string_utils
from src.utils.string_utils import slugify


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


def test_slugify_caches_repeated_inputs(monkeypatch):
    slugify.cache_clear()
    original_sub = string_utils.re.sub
    call_count = {"count": 0}

    def counting_sub(pattern, replacement, text):
        call_count["count"] += 1
        return original_sub(pattern, replacement, text)

    monkeypatch.setattr(string_utils.re, "sub", counting_sub)

    assert slugify("Hello World") == "hello-world"
    assert slugify("Hello World") == "hello-world"
    assert call_count["count"] == 2
