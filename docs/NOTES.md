---
layout: default
title: Design Notes
---

# Design note: untangling `ItemService`

## The problem

`src/services/item_service.py` mixed two unrelated concerns in one class:

- **Pure domain rules** — `calculate_priority` and `validate_item` compute a
  result purely from their inputs. They have no business touching a database,
  yet they lived on a class whose constructor demanded a `db` handle.
- **Stateful orchestration** — `batch_update_status` reads and writes records
  through `self.db`.

Because the pure rules were bolted onto a stateful object, testing them meant
constructing a `db`, and the implicit `datetime.utcnow()` calls made results
non-deterministic.

## The shape now

A pure core plus a thin adapter:

```
src/services/items/
    priority.py     # scoring: PriorityInputs, score(), level_for_score(), classify()
    validation.py   # validate() -> ValidationResult
    status.py       # classify_status_change(), apply_status_change()
    service.py      # ItemService: the only module that touches the database
    __init__.py     # public surface
```

- **Pure core** (`priority`, `validation`, `status`): no I/O, no database, no
  hidden clock. The current time is an injected `now` argument that defaults to
  `datetime.utcnow()`, so production behavior is unchanged while tests stay
  deterministic.
- **Thin adapter** (`service.ItemService`): keeps the `db` dependency and the
  one genuinely stateful method, `batch_update_status`. It delegates every rule
  to the core and does nothing but read, decide (via the core), and write.

`src/services/item_service.py` is now a shim that re-exports `ItemService`, so
`from src.services.item_service import ItemService` still works.

## Behavior preserved

- Priority weights, the stale-age rule (`age > 30`), and the 80/50/20
  thresholds are unchanged; levels are still the strings `critical` / `high` /
  `medium` / `low`.
- Validation produces the same messages in the same order. `validate_item`
  returns a `ValidationResult` `NamedTuple`, which unpacks and compares exactly
  like the previous `(is_valid, errors)` tuple.
- `batch_update_status` returns the same `{"updated", "failed", "skipped"}`
  payload with the same `"not found"` / `"already in state"` reasons, and still
  mutates each record in place before handing it to `db.save`.

The public methods gained an optional `now` parameter; existing call sites that
omit it behave as before.

## Tests

- `tests/test_item_priority.py` — scoring math, score-to-level thresholds, the
  stale-age boundary, and classification edge cases.
- `tests/test_item_validation.py` — each rule, message ordering, and tuple
  compatibility.
- `tests/test_item_service.py` — adapter delegation, `batch_update_status`
  outcomes against a fake in-memory db, and the legacy import path.
