from datetime import datetime
from typing import Optional, List, Dict, Any
from src.utils.filters import aggregate_items, build_query_filter, FilterError


class ItemService:
    def __init__(self, db):
        self.db = db

    def calculate_priority(self, item: Dict[str, Any]) -> str:
        """Calculate an item's priority from urgency, criticality, and age.

        Args:
            item: Item data with optional `urgency`, `is_critical`, and `created_at`.

        Returns:
            Priority level as one of: `low`, `medium`, `high`, or `critical`.
        """
        age_days = (datetime.utcnow() - item.get("created_at", datetime.utcnow())).days
        base_score = item.get("urgency", 0) * 10

        if item.get("is_critical"):
            base_score += 50

        if age_days > 30:
            base_score += age_days * 0.5

        if base_score >= 80:
            return "critical"
        elif base_score >= 50:
            return "high"
        elif base_score >= 20:
            return "medium"
        return "low"

    def validate_item(self, data: dict) -> tuple:
        errors = []
        if not data.get("name") or len(data["name"].strip()) == 0:
            errors.append("Name is required")
        if data.get("quantity", 0) < 0:
            errors.append("Quantity cannot be negative")
        if data.get("due_date"):
            try:
                due = datetime.fromisoformat(data["due_date"])
                if due < datetime.utcnow():
                    errors.append("Due date cannot be in the past")
            except ValueError:
                errors.append("Invalid date format")
        return len(errors) == 0, errors

    def batch_update_status(
        self, ids: list, new_status: str, updated_by: str
    ) -> dict:
        results = {"updated": [], "failed": [], "skipped": []}
        for id in ids:
            record = self.db.get(id)
            if record is None:
                results["failed"].append({"id": id, "reason": "not found"})
                continue
            if record.get("status") == new_status:
                results["skipped"].append({"id": id, "reason": "already in state"})
                continue
            record["status"] = new_status
            record["updated_by"] = updated_by
            record["updated_at"] = datetime.utcnow()
            self.db.save(record)
            results["updated"].append(id)
        return results

    def get_status_summary(
        self,
        include_status: Optional[List[str]] = None,
        exclude_status: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get summary statistics grouped by status.

        This method demonstrates proper handling of mutable default arguments
        by using None as default and initializing inside the function.

        Args:
            include_status: List of statuses to include in summary
            exclude_status: List of statuses to exclude from summary

        Returns:
            Dictionary containing status summary and aggregations
        """
        # Properly handle mutable defaults - DO NOT use [] as default
        if include_status is None:
            include_status = []
        if exclude_status is None:
            exclude_status = []

        # Get all items from database
        all_items = list(self.db.values()) if hasattr(self.db, "values") else []

        # Filter based on status criteria
        filtered_items = []
        for item in all_items:
            item_status = item.get("status")

            # Apply include filter
            if include_status and item_status not in include_status:
                continue

            # Apply exclude filter
            if exclude_status and item_status in exclude_status:
                continue

            filtered_items.append(item)

        # Use the aggregate utility to group by status
        aggregations = {
            "urgency": "avg",
            "quantity": "sum",
        }

        status_groups = aggregate_items(
            filtered_items, group_by="status", aggregations=aggregations
        )

        return {
            "total_items": len(filtered_items),
            "status_breakdown": status_groups,
            "filter_applied": {
                "include_status": include_status,
                "exclude_status": exclude_status,
            },
        }

    def build_item_filter(
        self,
        status_list: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build a filter configuration for querying items.

        Demonstrates use of the build_query_filter utility with proper
        mutable default handling.

        Args:
            status_list: List of acceptable status values
            tags: List of required tags

        Returns:
            Filter configuration dictionary
        """
        # Use the utility function which properly handles mutable defaults
        return build_query_filter(
            include_status=status_list, exclude_status=None, tags=tags
        )
