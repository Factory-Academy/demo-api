class AppError(Exception):
    """Base class for application exceptions."""
    pass


class ResourceNotFoundError(AppError):
    """Raised when a requested resource is not found."""
    def __init__(self, resource_type: str, resource_id: int):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with ID {resource_id} not found")


class ValidationError(AppError):
    """Raised when data validation fails."""
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Validation failed: {', '.join(errors)}")
