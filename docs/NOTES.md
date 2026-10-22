---
layout: default
title: Domain Model Notes
---

# Dataclass Domain Models

This change introduces a small dataclass domain layer under `src/domain/` and
migrates the routes and the item service off the loose `dict` structures they
passed around before.

## Why

The routes stored records as `List[dict]` and the service accepted and returned
plain dicts and tuples. That meant:

- field names were stringly-typed and easy to misspell silently,
- the "shape" of a record lived only in scattered literals,
- business logic (priority, validation, batch updates) returned nested
  dict-of-lists and tuples with no names.

## What changed

| Area | Before | After |
|---|---|---|
| `src/domain/models.py` | — | `ItemRecord`, `WidgetRecord` dataclasses |
| `src/domain/priority.py` | inline `if/elif` on magic numbers | `Priority` enum + `compute_priority()` |
| `src/domain/results.py` | tuple / dict-of-lists | `ValidationResult`, `BatchUpdateResult`, `BatchOutcome` |
| `src/domain/repository.py` | — | `InMemoryRepository` over `ItemRecord` |
| `src/routes/item_routes.py` | `List[dict]` + dict spreads | stores `ItemRecord`, uses `create()` / `apply_update()` |
| `src/routes/widget_routes.py` | `List[dict]` | stores `WidgetRecord` |
| `src/services/item_service.py` | dict in, tuple/dict out | dataclasses in and out |

## Design notes

- **Pydantic stays at the edge.** The schemas in `src/models` still parse
  requests and serialize responses. Because they set `from_attributes = True`,
  they serialize directly from the dataclass instances the routes now return,
  so the HTTP contract is unchanged.
- **Unknown fields fail loudly.** `ItemRecord.create` / `apply_update` reject
  keys that are not model fields, replacing the silent `{**a, **b}` merge.
  `apply_update` also refuses to overwrite `id` and `created_at`.
- **`Priority` subclasses `str`.** Existing comparisons against `"critical"`
  and JSON serialization keep working.
- **`ValidationResult` stays unpackable.** It is truthy on success and still
  supports `ok, errors = validate_item(...)` for callers written against the
  old tuple return.
- **Deterministic time.** Helpers accept an optional `now` so tests pin
  timestamps instead of racing `datetime.utcnow()`.

## Tests

- `tests/test_domain_models.py` — dataclass construction, update rules,
  priority buckets, stale-item aging.
- `tests/test_item_service.py` — validation, priority delegation, batch update
  outcomes and persistence.
- `tests/test_items.py` / `tests/test_widgets.py` — route-level create, update,
  delete, and 404 behavior over the migrated stores.
