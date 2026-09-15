import re


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


def to_title_case(text: str) -> str:
    """
    Normalize whitespace and convert text to title case.
    """
    normalized = " ".join(text.split())
    return normalized.title()
