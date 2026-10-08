from src.utils.string_utils import slugify


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
