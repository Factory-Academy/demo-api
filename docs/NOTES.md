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

### Boundary coercion and edge cases

`src/domain/coercion.py` centralizes how loose, externally-sourced values are
turned into typed record fields, so every `from_mapping` parses the same way and
fails the same way:

- **Booleans.** `coerce_bool` understands the usual string spellings
  (`"true"/"1"/"yes"` and `"false"/"0"/"no"/""`) and rejects anything else.
  This closes the trap where `bool("false")` is `True`, which previously could
  flip `is_critical` on when migrating stored payloads.
- **Integers.** `coerce_int` rejects `bool` (an `int` subclass) and unparseable
  values with a field-named `ValueError` instead of a bare `int()` message.
- **Dates.** `coerce_datetime` treats `None` and blank strings as "not set"
  (falling back to the default) and raises on a non-blank, non-ISO string.
- **Required fields.** `require` turns a missing `id`/`name`/`item_id` into a
  clear `ValueError` rather than a `KeyError`.
- **Priority scores.** `Priority.from_score` rejects non-numeric and non-finite
  scores. `NaN` is the dangerous case: it compares `False` against every
  threshold and would otherwise be silently bucketed as `LOW`.
- **Safe updates.** `with_changes` guards against unknown field names via
  `ensure_known_fields`, so a typo surfaces the offending name and record type
  instead of a generic `dataclasses.replace` `TypeError`.
- **Validation.** `ItemService.validate_item` also rejects a negative
  `urgency`, which would otherwise push the priority score below zero.

### Migrated call sites

- `src/services/item_service.py` — operates on `ItemRecord`, returns `Priority`,
  `ValidationResult`, and `BatchUpdateResult`.
- `src/services/widget_service.py` — returns `WidgetStats` and `WidgetRecord`.
- `src/routes/item_routes.py` / `src/routes/widget_routes.py` — the in-memory
  stores hold dataclass records; FastAPI serializes them through the existing
  Pydantic response models (`from_attributes = True`).

### Tests

- `tests/test_domain.py` — dataclass behavior and edge cases.
- `tests/test_coercion.py` — the boundary coercion helpers in isolation.
- `tests/test_item_service.py` — scoring thresholds, validation rules, and batch
  update outcomes against an in-memory `FakeDB`.
