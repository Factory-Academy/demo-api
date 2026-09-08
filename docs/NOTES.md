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

## Rate Limiting (`src/utils/rate_limiter/`)

The rate limiter throttles expensive or abuse-prone operations using the
**token-bucket** algorithm. A bucket holds up to `capacity` tokens and refills
continuously at `refill_rate` tokens per second. Each request spends one or
more tokens; when the bucket is short, the request is rejected. This permits
short bursts up to `capacity` while enforcing a steady long-run rate.

### Package layout

The limiter is a small package of focused modules; the public names are
re-exported from the package root, so `from src.utils.rate_limiter import
RateLimiter` still works.

- `validation.py` — shared numeric guardrails (finite, positive, in-range) and
  the `TOKEN_EPSILON` tolerance constant.
- `errors.py` — the `RateLimitExceeded` exception.
- `bucket.py` — the single-bucket `TokenBucket`.
- `limiter.py` — the keyed `RateLimiter` registry.

### API

- `TokenBucket(capacity, refill_rate, initial_tokens=None, time_func=...)` — a
  single bucket.
  - `try_consume(tokens=1) -> bool` — spend tokens, returning success.
  - `consume(tokens=1)` — spend tokens or raise `RateLimitExceeded`.
  - `available_tokens` — current balance after refill.
  - `time_until_available(tokens=1)` — seconds until a request would succeed,
    or `None` if it can never be satisfied.
  - `reset()` — refill to capacity.
- `RateLimiter(capacity, refill_rate, time_func=...)` — a registry of buckets
  keyed by an arbitrary string (user id, API key, IP), created lazily.
  - `allow(key, tokens=1) -> bool`, `check(key, tokens=1)` (raises),
    `tokens_remaining(key)`, `reset(key=None)`.
- `RateLimitExceeded` — carries `retry_after` (seconds, or `None`) and the
  offending `key`.

### Edge cases handled

- Invalid config (`capacity <= 0`, `refill_rate < 0`) and invalid requests
  (`tokens <= 0`) raise `ValueError`.
- **Non-finite numbers** (`NaN`, `+/-inf`) are rejected wherever a rate or a
  token count is accepted. `NaN` compares `False` against every threshold, so a
  plain `capacity <= 0` guard would let it through and silently corrupt a
  bucket's balance; validation now catches it up front. The checks live in one
  place (`validation.py`) so every entry point shares the same rules.
- **Floating-point tolerance**: token balances are refilled continuously as
  floats, so repeated fractional arithmetic can leave a value a hair below a
  whole number. Comparisons allow a small `TOKEN_EPSILON` of slack so an exact
  request is never rejected by rounding dust, and consumption clamps at zero so
  the balance never underflows to a tiny negative.
- Requests larger than `capacity` are rejected with `retry_after=None` since
  they can never succeed.
- A `refill_rate` of 0 acts as a fixed, non-renewing quota.
- `initial_tokens` is clamped to `[0, capacity]`.
- A non-monotonic clock stepping backwards never removes tokens.
- Consumption is guarded by a lock for safe concurrent use.

### Time injection

Both classes accept a `time_func` (defaulting to `time.monotonic`). Tests inject
a fake clock to advance time deterministically without sleeping.

### Integration

`ItemService` accepts an optional `rate_limiter`. When provided,
`batch_update_status` charges one token per requested id against the acting
user's key before touching any records, so a single caller cannot monopolize
batch updates. When omitted, the service is unchanged.
