import re


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.

    Args:
        text: The input string to slugify

    Returns:
        A lowercase string with spaces/underscores replaced by hyphens,
        special characters removed, and no duplicate hyphens
    """
    # Convert to lowercase
    slug = text.lower()

    # Replace spaces and underscores with hyphens
    slug = slug.replace(" ", "-").replace("_", "-")

    # Remove all non-alphanumeric characters except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Replace multiple consecutive hyphens with a single hyphen
    slug = re.sub(r"-+", "-", slug)

    # Strip leading and trailing hyphens
    slug = slug.strip("-")

    return slug
