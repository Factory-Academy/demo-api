import re

from src.utils.cache import ttl_cache


@ttl_cache(ttl_seconds=60, maxsize=256)
def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text
