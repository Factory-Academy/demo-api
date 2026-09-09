from src.utils.text import slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_with_special_characters():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Test@#$%String") == "teststring"


def test_slugify_with_underscores():
    assert slugify("some_variable_name") == "some-variable-name"


def test_slugify_with_multiple_spaces():
    assert slugify("too   many    spaces") == "too-many-spaces"


def test_slugify_with_mixed_case():
    assert slugify("MixedCaseString") == "mixedcasestring"


def test_slugify_with_numbers():
    assert slugify("Version 2.0") == "version-20"


def test_slugify_strips_leading_trailing_hyphens():
    assert slugify("-leading and trailing-") == "leading-and-trailing"


def test_slugify_empty_string():
    assert slugify("") == ""


def test_slugify_only_special_characters():
    assert slugify("@#$%") == ""


def test_slugify_none_input():
    assert slugify(None) == ""


def test_slugify_whitespace_only():
    assert slugify("   ") == ""
    assert slugify("\t\n") == ""
