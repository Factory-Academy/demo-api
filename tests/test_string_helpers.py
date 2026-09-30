import pytest
from src.utils.string_helpers import slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_with_special_characters():
    assert slugify("Product Name!") == "product-name"
    assert slugify("Test@Example#123") == "testexample123"


def test_slugify_with_extra_whitespace():
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_slugify_with_underscores():
    assert slugify("snake_case_text") == "snake-case-text"


def test_slugify_already_slug():
    assert slugify("already-a-slug") == "already-a-slug"


def test_slugify_empty_string():
    assert slugify("") == ""


def test_slugify_only_special_characters():
    assert slugify("!!!@@@###") == ""


def test_slugify_mixed_case():
    assert slugify("MixedCaseText") == "mixedcasetext"
