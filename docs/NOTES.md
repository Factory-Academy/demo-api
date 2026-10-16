# Documentation Notes

## Module: `src/services/item_service.py`

The `ItemService` module handles core business logic for item management within the application. Its primary responsibilities include:

- **Priority Calculation**: Determines item priority (critical, high, medium, low) based on age, urgency, and criticality markers.
- **Validation**: Enforces business rules for item data, such as requiring names and ensuring dates are valid and in the future.
- **Batch Operations**: Manages bulk updates to item statuses with detailed result reporting.
