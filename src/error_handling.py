from typing import Sequence


class ResourceNotFoundError(Exception):
    def __init__(self, resource: str, resource_id: int):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} with id {resource_id} was not found")


def get_resource_by_id(records: Sequence[dict], resource: str, resource_id: int) -> dict:
    for record in records:
        if record["id"] == resource_id:
            return record
    raise ResourceNotFoundError(resource=resource, resource_id=resource_id)
