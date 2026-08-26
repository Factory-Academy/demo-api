from src.services.item_service import slugify


def test_slugify_converts_text_to_url_safe_slug():
    assert slugify("  Hello, World!  ") == "hello-world"
