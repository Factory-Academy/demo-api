"""String utility functions."""

import re


def slugify(text: str) -> str:
    """
    Convert a string to a URL-safe slug.

    Args:
        text: The string to slugify

    Returns:
        A lowercase string with spaces replaced by hyphens and special characters removed

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("  Product Name! ")
        'product-name'
        >>> slugify("Test@Example#123")
        'testexample123'
    """
    # Convert to lowercase and strip whitespace
    text = text.lower().strip()
    # Replace spaces and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove all non-alphanumeric characters except hyphens
    text = re.sub(r"[^\w-]", "", text)
    # Replace multiple hyphens with a single hyphen
    text = re.sub(r"-+", "-", text)
    # Remove leading and trailing hyphens
    text = text.strip("-")
    return text
