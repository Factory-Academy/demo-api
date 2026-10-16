import re
import unicodedata


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[-\s]+", "-", text)
