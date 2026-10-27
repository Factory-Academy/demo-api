# In-process events (`src/events`)

A small, dependency-free publish/subscribe layer for decoupling side effects
(audit logging, notifications, cache invalidation) from the request path.
Everything runs synchronously in the current process; there is no broker,
queue, or network hop.

## Concepts

- **Event** — an immutable (`frozen`) dataclass describing something that
  happened. Concrete events live in `src/events/domain.py`
  (`ItemCreated`, `ItemUpdated`, `ItemDeleted`) and subclass `Event`.
- **EventBus** — dispatches a published event to every subscribed handler.
- **Subscription** — the handle returned by `subscribe`; call
  `.unsubscribe()` or use it as a context manager.
- **AuditLog** — an example subscriber that records every event it receives.

## Typed dispatch

Handlers subscribe to a concrete event type. When an event is published, the
bus invokes handlers registered for the event's type **and any of its base
types**, so subscribing to the `Event` base receives everything:

```python
from src.events import EventBus, Event, ItemCreated

bus = EventBus()
bus.subscribe(ItemCreated, lambda e: print("created", e.item_id))
bus.subscribe(Event, lambda e: print("any event:", e.event_name))

bus.publish(ItemCreated(item_id=1, name="Widget", status="active"))
# -> created 1
# -> any event: ItemCreated
```

## Guarantees and edge cases

- **Handler isolation** — a handler that raises never stops the others; the
  failure is routed to the bus's `on_error` callback (defaults to logging).
- **Re-entrancy** — handlers are invoked outside the internal lock, so a
  handler may safely publish, subscribe, or unsubscribe. Changes take effect
  on the *next* publish, not the one in flight.
- **Idempotent subscribe** — subscribing the same handler twice registers it
  once.
- **`subscribe_once`** — fires a handler for a single event, then removes it
  (even if that handler raises).
- **Thread-safe** — registration and dispatch are guarded by a re-entrant
  lock.
- **Validation** — publishing a non-`Event`, or subscribing a non-callable or
  a type that is not an `Event` subclass, raises `TypeError`.

## How it's wired into the app

`src/main.py` attaches a process-wide `AuditLog` to the default bus:

```python
from src.events import AuditLog, get_event_bus

audit_log = AuditLog()
audit_log.attach(get_event_bus())
```

The item CRUD endpoints (`src/routes/item_routes.py`) publish on the default
bus returned by `get_event_bus()`:

- `POST /items/` → `ItemCreated`
- `PUT /items/{id}` → `ItemUpdated` (with the tuple of changed fields)
- `DELETE /items/{id}` → `ItemDeleted`

Failed operations (validation errors, unknown ids) publish nothing.

## Adding a new subscriber

```python
from src.events import get_event_bus, ItemCreated

def send_welcome(event: ItemCreated) -> None:
    ...  # your side effect

subscription = get_event_bus().subscribe(ItemCreated, send_welcome)
# later: subscription.unsubscribe()
```

## Tests

- `tests/test_event_bus.py` — unit coverage for the bus, domain events, and
  audit log (standard library only).
- `tests/test_item_events.py` — integration coverage proving the CRUD flow
  emits the right events.

Run with `pytest tests/ -v`.

---

# Token-bucket rate limiter (`src/utils/rate_limiter`)

A small, dependency-free token-bucket rate limiter. A bucket holds up to
`capacity` tokens and refills continuously at `refill_rate` tokens per second.
Each request spends one or more tokens; when the bucket is short, the request
is rejected. This permits short bursts up to `capacity` while holding the
long-run average to `refill_rate`.

## Layout

- `validation.py` — numeric guardrails (`finite`, positive, in-range) shared by
  both classes, plus `TOKEN_EPSILON`.
- `errors.py` — the `RateLimitExceeded` exception.
- `bucket.py` — the single-bucket `TokenBucket`.
- `limiter.py` — the keyed `RateLimiter`.

Import the public names straight from the package:

```python
from src.utils.rate_limiter import TokenBucket, RateLimiter, RateLimitExceeded
```

## `TokenBucket`

One independent allowance.

```python
bucket = TokenBucket(capacity=5, refill_rate=1)   # burst 5, 1 token/sec

bucket.try_consume()            # -> True/False, never raises
bucket.consume(2)               # spends 2 or raises RateLimitExceeded
bucket.available_tokens()       # current balance after refill
bucket.time_until_available(3)  # seconds until 3 tokens, or None if impossible
bucket.reset()                  # refill to capacity
```

Inject a clock with `time_func` for deterministic tests (defaults to
`time.monotonic`).

## `RateLimiter`

A keyed registry that lazily creates one bucket per key — a user id, API key,
or IP — all sharing the same `capacity` and `refill_rate`.

```python
limiter = RateLimiter(capacity=100, refill_rate=10)

if limiter.allow(user_id):      # True/False
    handle_request()

limiter.check(user_id)          # raises RateLimitExceeded (with .key set)
limiter.tokens_remaining(user_id)
limiter.reset(user_id)          # or reset() to drop every bucket
```

## Guarantees and edge cases

- **Thread-safe** — every bucket guards its balance with a lock, so concurrent
  callers never oversell the allowance.
- **Non-finite input rejected** — `NaN`/`inf` for capacity, rate, or a token
  request raise `ValueError` up front. `NaN` compares `False` against every
  threshold, so catching it early prevents a silently poisoned bucket.
- **Float-dust tolerant** — a request for exactly the available balance is not
  rejected by accumulated floating-point error (`TOKEN_EPSILON`).
- **Monotonic-safe** — a clock that steps backwards never adds tokens.
- **Unsatisfiable requests** — asking for more than `capacity`, or for a
  drained bucket with `refill_rate == 0`, reports `retry_after=None`.

## How it's wired into the app

`ItemService` accepts an optional `rate_limiter`. When supplied,
`batch_update_status` spends one token per record it actually writes (lookups
and no-op skips cost nothing) and routes a caller's overflow into a
`rate_limited` bucket in the result, so one user cannot monopolize a batch:

```python
service = ItemService(db, rate_limiter=RateLimiter(capacity=100, refill_rate=10))
result = service.batch_update_status(ids, "closed", updated_by="alice")
result["rate_limited"]  # ids dropped once alice's bucket emptied
```

## Tests

- `tests/test_rate_limiter.py` — unit coverage for the bucket, limiter, and
  validation helpers, including refill timing, bursts, concurrency, and edge
  cases (standard library only).
- `tests/services/test_item_service_rate_limit.py` — integration coverage for
  the `ItemService` batch flow.

Run with `pytest tests/ -v`.
