# Item data-processing: edge-case hardening

## The bug class

`ItemService` (`src/services/item_service.py`) held three data-processing
helpers that each assumed perfectly-formed input. A single missing key, a
wrong-typed field, or an unusual collection turned an ordinary request into an
uncaught exception:

| Helper | Trigger | Old behaviour |
|---|---|---|
| `calculate_priority` | `created_at` missing | `KeyError` |
| `calculate_priority` | `created_at` is an ISO string or timezone-aware | `TypeError` on subtraction |
| `calculate_priority` | `urgency` is `None` / non-numeric | `TypeError` |
| `validate_item` | `name` is a non-string (e.g. `int`) | `AttributeError` on `.strip()` |
| `validate_item` | `quantity` is `None` / non-numeric | `TypeError` on `< 0` |
| `validate_item` | `due_date` is a non-string (e.g. `int`) | `TypeError` (only `ValueError` was caught) |
| `batch_update_status` | `ids` is `None` | `TypeError` on iteration |
| `batch_update_status` | `ids` is a bare string | iterated character-by-character |
| `batch_update_status` | duplicate ids | processed more than once |
| `batch_update_status` | very large `ids` | unbounded work |
| `batch_update_status` | any record | mutated the stored dict in place (aliasing) |

## The fix

The helpers were split into small, pure, individually testable functions under
`src/services/items/`:

- `coerce.py` — defensive coercion (`as_number`, `as_text`, `as_datetime`) that
  falls back to a safe default instead of raising. Booleans are not treated as
  numbers; `NaN`/`inf` are rejected; timezone-aware datetimes are normalised to
  naive UTC so comparisons never mix aware and naive values.
- `priority.py` — `age_in_days`, `urgency_score`, `criticality_bonus`,
  `aging_bonus`, `priority_score`, `score_to_label`, and the `calculate_priority`
  wrapper. A non-mapping item scores `0.0` (label `low`) rather than raising.
- `validation.py` — one validator per field, each returning `None` or a single
  error string, plus `collect_errors` / `validate_item`.
- `batch.py` — `normalize_ids` (rejects strings/bytes, de-duplicates, accepts
  mapping keys), `enforce_batch_limit`, `plan_update` (pure classification), and
  `apply_update` (returns a new dict, never mutates the caller's record).
- `errors.py` — `ItemDataError` for guardrail violations a caller must fix
  (missing target status, non-iterable ids, oversized batch).

`ItemService` keeps its original public API
(`calculate_priority`, `validate_item`, `batch_update_status`) and now simply
orchestrates these helpers with the database.

## Intentional behaviour changes

- Negative or malformed `urgency` now contributes `0` instead of a negative or
  crashing score.
- Future `created_at` clamps age to `0` days.
- `batch_update_status` de-duplicates ids and enforces `MAX_BATCH_SIZE`
  (1000); an empty or `None` id list is a no-op returning empty buckets.
- A missing/empty `new_status` raises `ItemDataError` rather than silently
  writing a blank status.

## Tests

Regression coverage lives across:

- `tests/test_coerce.py`
- `tests/test_priority.py`
- `tests/test_validation.py`
- `tests/test_batch.py`
- `tests/test_item_service.py`

Each previously-crashing input listed above has a dedicated regression test.
Run them with `pytest tests/ -v`.
