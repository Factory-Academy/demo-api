---
layout: default
title: Architecture Notes
---

# Architecture Notes

## Services Module (`src/services`)

The services layer encapsulates business logic, keeping it separate from routing and data models. This separation makes business rules easier to test, reuse, and customize during demo prep.

### Responsibilities

- **Priority calculation**: Scoring items based on urgency, age, and critical flags
- **Validation logic**: Input validation with detailed error messages
- **Batch operations**: Multi-record status updates with granular results (updated/failed/skipped)
- **Retry utilities**: Simple retry wrapper for transient failures

### Why It Matters for Demos

During demo prep, the `{{DOMAIN_MODEL}}` placeholder gets replaced (e.g., `Item` → `Patient`), and industry-specific business logic can be planted here. For example:

- Healthcare: priority based on patient acuity scores
- Fintech: validation rules for transaction limits
- E-commerce: batch inventory updates

The service layer is where domain expertise lives, making it a natural spot for:
- Demo moments showcasing Droid's ability to understand business context
- Code review targets (e.g., missing edge case handling)
- Feature implementation requests that require domain logic changes

### Current Implementation

`item_service.py` contains:
- `ItemService` class with DB-backed CRUD business logic
- `retry()` helper function for fault tolerance
- Pure functions for scoring and validation (easy to unit test)

No external service calls yet — those get added during customization if the prospect's stack includes third-party integrations.
