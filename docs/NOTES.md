# Design note: splitting `ItemService`

## The problem

`src/services/item_service.py` had grown into a tangled module. A single
`ItemService` class mixed two very different kinds of code:

- **Pure business rules** — `calculate_priority` (scoring) and `validate_item`
  (payload checks). These depend only on their inputs.
- **Side-effecting I/O** — `batch_update_status`, which reads records from
  `self.db`, mutates them, and writes them back.

Because the rules were welded to the class and to `datetime.utcnow()`, testing
them meant constructing a service, and testing the batch logic meant reasoning
about database calls at the same time as the branching rules.

## The shape now

```
src/services/
  item_service.py          # thin adapter: fetch -> decide -> save
  items/
    __init__.py            # re-exports the pure API
    priority.py            # priority_score, label_for_score, calculate_priority
    validation.py          # per-field validators + validate_item
    batch.py               # classify_record, status_fields
```

**Pure core (`src/services/items/`)** holds every rule. No module here reads a
database or the clock on its own. The wall-clock time is an injectable `now`
argument that defaults to `datetime.utcnow()`, so production behavior is
unchanged while tests can pin the clock and stay deterministic.

- `priority.py` separates the numeric `priority_score` from `label_for_score`,
  so the raw score is reusable (for example, to sort a queue) and the
  thresholds live in one ordered table.
- `validation.py` breaks each check into a small function returning an error
  message or `None`, then aggregates them into the existing
  `(is_valid, errors)` tuple.
- `batch.py` exposes `classify_record` (update / skip / fail) and
  `status_fields` (the changes to apply). All batch branching is pure and
  database-free.

**Thin adapter (`item_service.py`)** keeps the same public class and method
signatures. `batch_update_status` now just walks the ids, asks the core to
classify each fetched record, applies `status_fields` and saves on an update,
and buckets the result. Existing callers need no changes.

## Behavior preservation

The public API (`ItemService(db)` with `calculate_priority`, `validate_item`,
`batch_update_status`) is identical, and the returned shapes match exactly:
priority labels, the `(bool, errors)` validation tuple, and the
`{updated, failed, skipped}` result dict with the same `reason` strings.

One deliberate, non-observable refinement: the batch now pins a single
timestamp per run, so every record updated in one call shares an `updated_at`
instead of drifting microseconds apart. The result dict is unaffected.

## Edge-case hardening (review follow-up)

The first cut of the pure core assumed well-formed payloads, so a malformed
optional field raised an unhandled `TypeError` from deep inside a rule instead
of being handled where the rule lives. That was tightened:

- **Shared coercion** — `items/coerce.py` adds `is_number` and `as_number`, the
  single definition of "a usable number". `bool` is treated as non-numeric on
  purpose: a boolean in a numeric field is a payload bug, not `1`.
- **Priority** — `priority_score` now reads urgency through `as_number`, so a
  missing, `None`, or non-numeric urgency contributes `0`, and a negative
  urgency is clamped to `0`. Clamping keeps the score non-negative, which is
  what makes the `label_for_score` floor genuinely unreachable rather than just
  unlikely.
- **Validation** — a `None` quantity is treated as unset (the historical `0`
  default) instead of crashing on `None < 0`; a non-numeric quantity now returns
  the explicit `"Quantity must be a number"`. Due-date parsing catches
  `TypeError` alongside `ValueError`, so a non-string date reports
  `"Invalid date format"` rather than propagating.

These are defensive refinements only: every previously valid payload keeps its
old result and the `(is_valid, errors)` / label shapes are unchanged.

## Testing

Each pure module has its own focused suite, and the adapter is tested against a
small in-memory `FakeDB`:

- `tests/test_item_priority.py` — scoring math, threshold boundaries, stale-age
  escalation, future-dated items, missing keys, and malformed/negative urgency.
- `tests/test_item_validation.py` — name/quantity/due-date rules, error
  accumulation, injected vs. default clock, and malformed quantity/date types.
- `tests/test_item_batch.py` — classification outcomes and field building.
- `tests/test_item_coerce.py` — the numeric coercion helpers.
- `tests/test_item_service.py` — adapter wiring: update/skip/fail partitioning,
  mixed batches, empty input, shared timestamp, in-place mutation.
