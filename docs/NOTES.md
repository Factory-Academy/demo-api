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

## Follow-up: edge-case hardening

Review feedback: the pure core trusted the shape of its input. Malformed
payloads leaked raw built-in exceptions instead of being handled by the domain
rules — a non-string `name` raised `AttributeError`, a non-numeric `quantity`
or `urgency` raised `TypeError`, a missing `created_at` raised `KeyError`, and
a timezone-aware `due_date` raised `TypeError` when compared with the naive
`now`.

The follow-up adds one small, I/O-free helper, `src/services/items/_coerce.py`,
and routes the untrusted-field handling through it:

- `is_number` / `number_or` — strict numeric detection for validation (which
  reports a problem) and lenient coercion for scoring (which has no error
  channel and defaults instead).
- `parse_timestamp` / `as_datetime` — parse ISO-8601 strings, accept a trailing
  `Z` on every supported Python version (not just 3.11+), and return `None`
  rather than raising on junk.
- `make_naive_utc` — normalise timestamps to naive UTC so aware and naive
  values can be compared without raising.

Behaviour changes are additive and backward compatible:

- `validate` gains two messages — `NAME_MUST_BE_TEXT` for a non-string name and
  `NON_NUMERIC_QUANTITY` for a non-number quantity — slotted into the existing
  name/quantity/due-date order. All previous messages, their order, and the
  `ValidationResult` tuple contract are unchanged.
- `priority` now treats a missing or unparseable `created_at` as "no staleness
  bonus" and a non-numeric `urgency` as `0`, so a bad item scores low instead
  of crashing. `PriorityInputs.created_at` is now `Optional[datetime]`.

Tests: `tests/test_item_coerce.py` covers the helper directly, and the priority
and validation suites gain cases for each malformed-input path above.
