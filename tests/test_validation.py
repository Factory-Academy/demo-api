import pytest
from src.services.items.validation import validate_tags

def test_validate_tags_no_mutation():
    """
    Ensure validate_tags does not mutate the passed forbidden list.
    """
    custom_forbidden = ["custom"]
    validate_tags(["safe"], forbidden=custom_forbidden)
    assert "restricted" not in custom_forbidden # Should NOT have been mutated
    
def test_validate_tags_logic():
    # 'restricted' should be forbidden by default
    errors = validate_tags(["restricted"])
    assert "Tag 'restricted' is forbidden" in errors
    
    # 'safe' should be allowed
    assert validate_tags(["safe"]) == []
