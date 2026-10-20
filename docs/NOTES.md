# Documentation Notes

## Module: `src/services/item_service.py`

The `ItemService` module handles core business logic for item management within the application. Its primary responsibilities include:

- **Priority Calculation**: Determines item priority (critical, high, medium, low) based on age, urgency, and criticality markers.
- **Validation**: Enforces business rules for item data, such as requiring names and ensuring dates are valid and in the future.
- **Batch Operations**: Manages bulk updates to item statuses with detailed result reporting.

## Module: `src/events/`

A lightweight, in-process publish/subscribe bus with typed events. It lets one
flow announce that something happened (an item was created, updated, deleted)
without knowing or caring who reacts.

### Pieces

- `base.py` — `Event`, the frozen dataclass every event derives from. It
  carries shared metadata (`event_id`, `occurred_at`, `name`).
- `domain.py` — concrete item events: `ItemCreated`, `ItemUpdated`,
  `ItemDeleted`, all sharing the `ItemEvent` base.
- `bus.py` — `EventBus` plus a process-wide default accessible via
  `get_event_bus()` (and `reset_event_bus()` for tests).
- `audit.py` — `AuditLog`, a reference subscriber that records every item
  event into a bounded in-memory trail.

### Behavior worth knowing

- **Typed, inheritance-aware dispatch.** Subscribe to a specific event
  (`ItemCreated`) or to a base (`ItemEvent`, or even `Event`) to receive every
  subtype. Most-derived handlers run first, then base handlers.
- **Error isolation.** A handler that raises never stops the others. Failures
  are collected into the `PublishResult` returned by `publish` and, if you pass
  `on_error` to the bus, forwarded there too.
- **Thread-safe.** Subscribe, unsubscribe, and publish are safe to call from
  multiple threads; the handler list is snapshotted before dispatch.
- **Unsubscribe cleanly.** `subscribe` returns a `Subscription` handle with
  `.unsubscribe()`; it also works as a context manager and supports one-shot
  delivery via `once=True`.

### Usage

```python
from src.events import ItemCreated, get_event_bus

bus = get_event_bus()

def notify(event: ItemCreated) -> None:
    print(f"item {event.item_id} created at {event.occurred_at}")

subscription = bus.subscribe(ItemCreated, notify)
result = bus.publish(ItemCreated(item_id=42, item={"id": 42, "name": "Widget"}))
assert result.ok  # every handler ran without raising

subscription.unsubscribe()  # stop listening
```

### Where it is wired in

`src/routes/item_routes.py` publishes an event after each create/update/delete.
On startup `src/main.py` attaches the default `AuditLog` to the default bus, and
`GET /items/events/audit` returns the recorded trail.
