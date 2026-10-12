from src.utils.string_utils import collapse_whitespace, slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_characters():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_whitespace():
    assert slugify("  Hello   World  ") == "hello-world"


def test_slugify_unicode():
    assert slugify("Héllö Wörld") == "hello-world"


def test_slugify_hyphens():
    assert slugify("hello--world") == "hello-world"


def test_slugify_empty():
    assert slugify("") == ""
    assert slugify(None) == ""  # type: ignore


def test_collapse_whitespace():
    assert collapse_whitespace("  Hello\t \nWorld  ") == "Hello World"
    assert collapse_whitespace("") == ""
