from src.services.item_service import slugify


def test_slugify_converts_to_lowercase_with_hyphens():
    assert slugify("Hello World") == "hello-world"


def test_slugify_collapses_non_alphanumeric_characters():
    assert slugify("  API---Demo___Feature  ") == "api-demo-feature"


def test_slugify_returns_empty_string_for_only_symbols():
    assert slugify("!!!") == ""
