# Documentation Notes

## Module: `src/services/item_service.py`

The `ItemService` module handles core business logic for item management within the application. Its primary responsibilities include:

- **Priority Calculation**: Determines item priority (critical, high, medium, low) based on age, urgency, and criticality markers.
- **Validation**: Enforces business rules for item data, such as requiring names and ensuring dates are valid and in the future.
- **Batch Operations**: Manages bulk updates to item statuses with detailed result reporting.

## Package: `src/domain/`

The domain package replaces the loose `dict` payloads that used to flow between
the routes and services with small, explicit dataclasses. Loose dicts made the
shape of a "record" or a "result" implicit and easy to get wrong; the dataclasses
make the fields, types, and defaults obvious and give us a single place to attach
behavior.

| Type | Replaces | Notes |
|---|---|---|
| `ItemRecord` | the stored item `dict` | Frozen (immutable + hashable). Updates go through `with_changes` / `with_status`, which return a fresh copy and refresh `updated_at`. |
| `WidgetRecord` | the stored widget `dict` | Frozen, same update pattern as `ItemRecord`. |
| `Priority` | the bare `"critical"`/`"high"`/... strings | `str` enum, so it stays `==` comparable to the old string values. `Priority.from_score` owns the threshold mapping. |
| `ValidationResult` | the `(bool, errors)` tuple | Truthy when valid; `raise_for_errors()` turns failures into a `ValueError`. |
| `BatchUpdateResult` / `BatchOutcome` | the `{"updated": [...], "failed": [...], ...}` dict | Typed accumulator; `to_dict()` renders the legacy response shape. |
| `WidgetStats` | the ad-hoc stats `dict` | Returned by `WidgetService.get_complex_widget_stats`. |

### Design choices

- **Frozen records.** Immutability means a record can be used as a cache key
  (`ItemService.calculate_priority` is memoized) and that batch updates cannot
  accidentally mutate state shared with another caller. Edits produce a new
  record via `dataclasses.replace`.
- **Pure scoring.** `ItemService.score` takes an optional `now` and has no side
  effects, so the priority thresholds are tested directly without the cache.
- **Boundary serialization.** `to_dict()` / `ItemRecord.from_mapping` convert to
  and from plain mappings for the API boundary and for migrating previously
  persisted payloads (`from_mapping` raises `ValueError` on an unparseable date).

### Migrated call sites

- `src/services/item_service.py` — operates on `ItemRecord`, returns `Priority`,
  `ValidationResult`, and `BatchUpdateResult`.
- `src/services/widget_service.py` — returns `WidgetStats` and `WidgetRecord`.
- `src/routes/item_routes.py` / `src/routes/widget_routes.py` — the in-memory
  stores hold dataclass records; FastAPI serializes them through the existing
  Pydantic response models (`from_attributes = True`).

### Tests

- `tests/test_domain.py` — dataclass behavior and edge cases.
- `tests/test_item_service.py` — scoring thresholds, validation rules, and batch
  update outcomes against an in-memory `FakeDB`.
