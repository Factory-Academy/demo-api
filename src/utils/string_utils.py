import re
import unicodedata
from typing import Optional

# Regex pattern to collapse consecutive hyphens and spaces into a single hyphen
COLLAPSE_PATTERN = r"[-\s]+"


def slugify(text: Optional[str]) -> str:
    """
    Convert a string to a URL-friendly slug.
    
    Args:
        text: A string to convert, or None.
        
    Returns:
        A URL-friendly slug, or an empty string if input is None or empty.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(COLLAPSE_PATTERN, "-", text)
