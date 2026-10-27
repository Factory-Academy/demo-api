# In-process events (`src/events`)

A small, dependency-free publish/subscribe layer for decoupling side effects
(audit logging, notifications, cache invalidation) from the request path.
Everything runs synchronously in the current process; there is no broker,
queue, or network hop.

# Retry Utility (`src/retry.py`)

A lightweight, generic retry helper for wrapping fallible operations.

## Usage

```python
from src.retry import retry

def unstable_call():
    # ... might raise ConnectionError
    return "success"

result = retry(unstable_call, attempts=3, exceptions=(ConnectionError,))
```

## Features

- **Generic** — Works with any callable returning any type.
- **Customizable** — Specify the number of attempts and which exceptions to catch.
- **Strict** — Validates that `attempts >= 1` and at least one exception type is provided.

## Tests

- `tests/test_retry.py` — unit tests for success, failure, and validation logic.

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
