class APIException(Exception):
    """Base class for all API exceptions."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundError(APIException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str, identifier: any):
        message = f"{resource} with identifier {identifier} not found"
        super().__init__(message, status_code=404)


class ValidationError(APIException):
    """Raised when validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
