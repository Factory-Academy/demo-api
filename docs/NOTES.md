---
layout: default
title: Module Notes
---

# Module Responsibilities

## item_service.py

The `ItemService` class encapsulates business logic for item management, keeping validation and calculations separate from route handlers.

### Core Responsibilities

| Method | Purpose |
|---|---|
| `calculate_priority()` | Computes priority level (critical/high/medium/low) based on urgency score, critical flag, and age |
| `validate_item()` | Enforces business rules: required name, non-negative quantity, future due dates |
| `batch_update_status()` | Updates status for multiple items in one operation, tracking success/failure/skip results |

### Helper Functions

| Function | Purpose |
|---|---|
| `retry()` | Generic retry wrapper for transient failures — attempts a function up to N times before raising |

### Design Notes

- All date operations use `datetime.utcnow()` for consistency
- Validation returns `(is_valid, errors)` tuple — errors list is empty on success
- Batch operations return structured results with separate lists for updated/failed/skipped IDs
- Database interactions go through the injected `db` dependency
