from src.utils.text import slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_with_special_characters():
    assert slugify("Python 3.11 Release!") == "python-3-11-release"


def test_slugify_multiple_spaces():
    assert slugify("Multiple   Spaces") == "multiple-spaces"


def test_slugify_with_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_already_lowercase():
    assert slugify("already-lowercase") == "already-lowercase"


def test_slugify_empty_string():
    assert slugify("") == ""


def test_slugify_only_special_characters():
    assert slugify("!!!") == ""


def test_slugify_mixed_case():
    assert slugify("CamelCase Text") == "camelcase-text"


def test_slugify_consecutive_special_chars():
    assert slugify("Hello -- World!!") == "hello-world"


def test_slugify_leading_trailing_special_chars():
    assert slugify("!!!Hello World!!!") == "hello-world"


def test_slugify_mixed_separators():
    assert slugify("Hello_World-Test") == "hello-world-test"
