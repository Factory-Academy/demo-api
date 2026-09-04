import re


def slugify(text: str) -> str:
    """
    Convert a string into a URL-friendly slug.

    Args:
        text: The input string to slugify

    Returns:
        A lowercase string with spaces and special characters replaced by hyphens

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Python 3.11 Release!")
        'python-3-11-release'
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces and non-alphanumeric characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug
