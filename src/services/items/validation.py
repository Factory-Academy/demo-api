"""Validation logic for items."""

from typing import List, Optional

def validate_tags(tags: List[str], forbidden: Optional[List[str]] = None) -> List[str]:
    """
    Validate a list of tags against forbidden words.
    """
    if forbidden is None:
        forbidden = ["admin", "system"]
    else:
        # Create a copy to avoid mutating the caller's list
        forbidden = list(forbidden)
        
    if "restricted" not in forbidden:
        forbidden.append("restricted")
        
    errors = []
    for tag in tags:
        if tag.lower() in forbidden:
            errors.append(f"Tag '{tag}' is forbidden")
            
    return errors
