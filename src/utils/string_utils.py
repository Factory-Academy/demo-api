import re


def slugify(text: str | None) -> str:
    """
    Convert a string to a URL-friendly slug.
    """
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text


def to_title_case(text: str | None) -> str:
    """
    Normalize whitespace and convert text to title case.
    """
    if not text:
        return ""

    normalized = " ".join(text.split())
    return normalized.title()
