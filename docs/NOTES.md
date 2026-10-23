# Item data-processing path: refactor and edge-case hardening

## Context

`ItemService` (in `src/services/item_service.py`) packed three unrelated
concerns into one class and assumed every input was well-formed. The priority
calculation, payload validation, and batch status update each crashed or
misbehaved on empty, malformed, or oversized inputs.

## What changed

The logic is split into small, pure, independently testable helpers.
`ItemService` is now a thin facade that keeps its original public interface
(`calculate_priority`, `validate_item`, `batch_update_status`), so existing
callers are unaffected.

```
src/services/
  item_service.py            facade wiring helpers to the datastore
  priority/
    __init__.py              calculate_priority() = score -> classify
    normalization.py         total coercion of created_at / urgency / flags
    scoring.py               pure component + total score computation
    classification.py        pure score -> label mapping
  items/
    __init__.py              re-exports validate_item / batch_update_status
    validation.py            one pure rule per field + aggregator
    batch.py                 pure planning + effectful apply, id hygiene
```

## Edge-case bugs fixed

### `calculate_priority`
- **Missing `created_at`** raised `KeyError`. Now treated as age 0.
- **ISO-string `created_at`** raised `TypeError` on datetime subtraction.
  `coerce_timestamp` parses ISO strings and tolerates a trailing `Z`
  (unsupported by `datetime.fromisoformat` on Python 3.9/3.10).
- **Future `created_at`** produced a negative age. Age is clamped at 0.
- **`urgency` of `None`** raised `TypeError`; a **string urgency** was silently
  multiplied as string repetition and then blew up at comparison time. Values
  are coerced to non-negative floats, with bad input falling back to 0.
- **Pathologically large urgency** produced an unbounded score. The score is
  clamped to `MAX_SCORE`.

### `validate_item`
- **Non-string `name`** raised `AttributeError` on `.strip()`.
- **Non-numeric `quantity`** raised `TypeError` on `< 0`.
- **Non-string `due_date`** raised `TypeError` in `fromisoformat`.
- **Trailing-`Z` due dates** failed to parse on Python 3.9/3.10.
- **Non-mapping payloads** now yield a single `"Invalid payload"` error instead
  of raising.

### `batch_update_status`
- **`None` or non-iterable `ids`** raised `TypeError`. Now returns an empty
  report via `normalize_ids`.
- **Duplicate ids** were processed more than once. Ids are de-duplicated with
  order preserved.
- **`None` ids** inside the list are dropped.
- **Empty/blank/non-string `new_status`** now fails every id with reason
  `"invalid status"` rather than writing a bad value.
- **Large id lists** are processed in chunks (`DEFAULT_CHUNK_SIZE`) to bound
  per-pass memory.

## Determinism

Every helper that reads the clock accepts an injectable `now` argument so the
regression suite is deterministic.

## Tests

Regression coverage lives in `tests/services/`:

- `test_priority_normalization.py`
- `test_priority_scoring.py`
- `test_priority_classification.py`
- `test_item_validation.py`
- `test_batch_update.py`
- `test_item_service.py`

Run just this suite with:

```bash
pytest tests/services/ -v
```
