from typing import Any, List, Optional, Union


class AppError(Exception):
    """Base class for application exceptions."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {"detail": self.message}


class ResourceNotFoundError(AppError):
    """Raised when a requested resource is not found."""
    def __init__(self, resource_type: str, resource_id: Any = None, **criteria):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.criteria = criteria

        if resource_id is not None:
            message = f"{resource_type} with ID {resource_id} not found"
        elif criteria:
            c_str = ", ".join(f"{k}={v}" for k, v in criteria.items())
            message = f"{resource_type} with {c_str} not found"
        else:
            message = f"{resource_type} not found"

        super().__init__(message=message, status_code=404)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "resource_type": self.resource_type,
        })
        if self.resource_id is not None:
            data["resource_id"] = self.resource_id
        if self.criteria:
            data["criteria"] = self.criteria
        return data


class ValidationError(AppError):
    """Raised when data validation fails."""
    def __init__(self, errors: Union[str, List[str]]):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        error_msg = "; ".join(str(e) for e in errors)
        super().__init__(
            message=f"Validation failed: {error_msg}",
            status_code=400
        )

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["errors"] = self.errors
        return data
