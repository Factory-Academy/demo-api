import threading
from dataclasses import dataclass
from datetime import timezone
from typing import List

import pytest

from src.events import (
    Event,
    EventBus,
    ItemCreated,
    ItemDeleted,
    ItemEvent,
    ItemUpdated,
    get_event_bus,
    reset_event_bus,
)


@dataclass(frozen=True)
class SampleEvent(Event):
    value: int = 0


@dataclass(frozen=True)
class ChildEvent(SampleEvent):
    extra: str = ""


def test_subscribe_and_publish_invokes_handler():
    bus = EventBus()
    received: List[SampleEvent] = []

    bus.subscribe(SampleEvent, received.append)
    result = bus.publish(SampleEvent(value=7))

    assert [e.value for e in received] == [7]
    assert result.handled == 1
    assert result.ok


def test_publish_with_no_subscribers_is_noop():
    bus = EventBus()
    result = bus.publish(SampleEvent(value=1))
    assert result.handled == 0
    assert result.ok


def test_handlers_run_in_subscription_order():
    bus = EventBus()
    order: List[str] = []

    bus.subscribe(SampleEvent, lambda e: order.append("first"))
    bus.subscribe(SampleEvent, lambda e: order.append("second"))
    bus.publish(SampleEvent())

    assert order == ["first", "second"]


def test_inheritance_dispatch_notifies_base_handlers():
    bus = EventBus()
    seen: List[str] = []

    bus.subscribe(SampleEvent, lambda e: seen.append("base"))
    bus.subscribe(ChildEvent, lambda e: seen.append("child"))

    bus.publish(ChildEvent(value=1, extra="x"))

    # Most-derived handlers first, then base handlers.
    assert seen == ["child", "base"]


def test_base_handler_does_not_receive_sibling_types():
    bus = EventBus()
    seen: List[str] = []

    bus.subscribe(ChildEvent, lambda e: seen.append("child"))
    bus.publish(SampleEvent(value=1))

    assert seen == []


def test_subscribe_is_idempotent_for_same_handler():
    bus = EventBus()
    calls: List[int] = []

    def handler(event: SampleEvent) -> None:
        calls.append(event.value)

    first = bus.subscribe(SampleEvent, handler)
    second = bus.subscribe(SampleEvent, handler)

    assert first is second
    assert bus.subscriber_count(SampleEvent) == 1

    bus.publish(SampleEvent(value=3))
    assert calls == [3]


def test_subscribe_same_handler_ignores_conflicting_once_flag():
    bus = EventBus()
    calls: List[int] = []

    def handler(event: SampleEvent) -> None:
        calls.append(event.value)

    # The persistent subscription wins; a later ``once=True`` call must not add
    # a duplicate (which would deliver twice) nor downgrade it to one-shot.
    first = bus.subscribe(SampleEvent, handler)
    second = bus.subscribe(SampleEvent, handler, once=True)

    assert first is second
    assert first.once is False
    assert bus.subscriber_count(SampleEvent) == 1

    bus.publish(SampleEvent(value=1))
    bus.publish(SampleEvent(value=2))

    # Each event delivered exactly once, and the handler is still subscribed.
    assert calls == [1, 2]
    assert bus.subscriber_count(SampleEvent) == 1


def test_unsubscribe_via_handle_stops_delivery():
    bus = EventBus()
    calls: List[int] = []

    subscription = bus.subscribe(SampleEvent, lambda e: calls.append(e.value))
    bus.publish(SampleEvent(value=1))
    subscription.unsubscribe()
    bus.publish(SampleEvent(value=2))

    assert calls == [1]
    assert not subscription.active


def test_double_unsubscribe_is_safe():
    bus = EventBus()
    subscription = bus.subscribe(SampleEvent, lambda e: None)
    subscription.unsubscribe()
    subscription.unsubscribe()  # must not raise
    assert bus.subscriber_count(SampleEvent) == 0


def test_unsubscribe_by_handler_returns_status():
    bus = EventBus()
    handler = lambda e: None

    bus.subscribe(SampleEvent, handler)
    assert bus.unsubscribe(SampleEvent, handler) is True
    assert bus.unsubscribe(SampleEvent, handler) is False


def test_subscription_context_manager_unsubscribes():
    bus = EventBus()
    calls: List[int] = []

    with bus.subscribe(SampleEvent, lambda e: calls.append(e.value)):
        bus.publish(SampleEvent(value=1))
    bus.publish(SampleEvent(value=2))

    assert calls == [1]


def test_once_subscription_fires_a_single_time():
    bus = EventBus()
    calls: List[int] = []

    bus.subscribe(SampleEvent, lambda e: calls.append(e.value), once=True)
    bus.publish(SampleEvent(value=1))
    bus.publish(SampleEvent(value=2))

    assert calls == [1]
    assert bus.subscriber_count(SampleEvent) == 0


def test_error_in_handler_is_isolated():
    bus = EventBus()
    calls: List[str] = []

    def boom(event: SampleEvent) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe(SampleEvent, boom)
    bus.subscribe(SampleEvent, lambda e: calls.append("ran"))

    result = bus.publish(SampleEvent())

    assert calls == ["ran"]
    assert result.handled == 1
    assert not result.ok
    assert len(result.errors) == 1
    assert isinstance(result.errors[0][1], RuntimeError)


def test_on_error_callback_receives_failure():
    captured: List[Exception] = []

    def on_error(handler, event, error):
        captured.append(error)

    bus = EventBus(on_error=on_error)
    bus.subscribe(SampleEvent, lambda e: (_ for _ in ()).throw(ValueError("x")))
    bus.publish(SampleEvent())

    assert len(captured) == 1
    assert isinstance(captured[0], ValueError)


def test_broken_on_error_callback_does_not_propagate():
    def on_error(handler, event, error):
        raise RuntimeError("error hook is broken")

    bus = EventBus(on_error=on_error)
    bus.subscribe(SampleEvent, lambda e: (_ for _ in ()).throw(ValueError("x")))

    # Must not raise despite both handler and error hook failing.
    result = bus.publish(SampleEvent())
    assert not result.ok


def test_subscribe_rejects_non_event_type():
    bus = EventBus()
    with pytest.raises(TypeError):
        bus.subscribe(str, lambda e: None)  # type: ignore[arg-type]


def test_subscribe_rejects_non_callable():
    bus = EventBus()
    with pytest.raises(TypeError):
        bus.subscribe(SampleEvent, 123)  # type: ignore[arg-type]


def test_publish_rejects_non_event():
    bus = EventBus()
    with pytest.raises(TypeError):
        bus.publish("not an event")  # type: ignore[arg-type]


def test_clear_all_and_by_type():
    bus = EventBus()
    bus.subscribe(SampleEvent, lambda e: None)
    bus.subscribe(ChildEvent, lambda e: None)

    bus.clear(ChildEvent)
    assert bus.subscriber_count(ChildEvent) == 0
    assert bus.subscriber_count(SampleEvent) == 1

    bus.clear()
    assert bus.subscriber_count() == 0


def test_handler_may_unsubscribe_during_publish():
    bus = EventBus()
    calls: List[int] = []

    def self_removing(event: SampleEvent) -> None:
        calls.append(event.value)
        subscription.unsubscribe()

    subscription = bus.subscribe(SampleEvent, self_removing)
    bus.publish(SampleEvent(value=1))
    bus.publish(SampleEvent(value=2))

    assert calls == [1]


def test_event_metadata_defaults_are_unique():
    first = SampleEvent()
    second = SampleEvent()
    assert first.event_id != second.event_id
    assert first.occurred_at is not None
    assert SampleEvent().name == "SampleEvent"


def test_event_occurred_at_is_timezone_aware_utc():
    event = SampleEvent()
    # A naive datetime (the old ``utcnow`` behavior) would serialize without an
    # offset and compare unsafely against aware timestamps.
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.utcoffset() == timezone.utc.utcoffset(None)
    # ISO output carries the explicit UTC offset.
    assert event.occurred_at.isoformat().endswith("+00:00")


def test_event_sequence_is_monotonic_and_unique():
    events = [SampleEvent() for _ in range(5)]
    sequences = [e.sequence for e in events]

    # Strictly increasing, so later-built events always sort after earlier ones.
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)
    assert all(b > a for a, b in zip(sequences, sequences[1:]))


def test_sequence_is_excluded_from_event_equality():
    # Two events sharing identity fields but built at different times (hence
    # different sequences) must still differ, because ``event_id`` is unique.
    first = SampleEvent(value=1)
    second = SampleEvent(value=1)
    assert first != second
    assert first.sequence != second.sequence


def test_domain_event_hierarchy():
    assert issubclass(ItemCreated, ItemEvent)
    assert issubclass(ItemUpdated, ItemEvent)
    assert issubclass(ItemDeleted, ItemEvent)
    assert issubclass(ItemEvent, Event)


def test_item_event_base_subscription_catches_all_subtypes():
    bus = EventBus()
    names: List[str] = []

    bus.subscribe(ItemEvent, lambda e: names.append(e.name))
    bus.publish(ItemCreated(item_id=1, item={"id": 1}))
    bus.publish(ItemUpdated(item_id=1, changes={"status": "done"}))
    bus.publish(ItemDeleted(item_id=1))

    assert names == ["ItemCreated", "ItemUpdated", "ItemDeleted"]


def test_default_bus_is_singleton_until_reset():
    first = get_event_bus()
    second = get_event_bus()
    assert first is second

    fresh = reset_event_bus()
    assert fresh is get_event_bus()
    assert fresh is not first


def test_concurrent_publish_delivers_every_event():
    bus = EventBus()
    lock = threading.Lock()
    received: List[int] = []

    def handler(event: SampleEvent) -> None:
        with lock:
            received.append(event.value)

    bus.subscribe(SampleEvent, handler)

    def publish_many(start: int) -> None:
        for i in range(start, start + 50):
            bus.publish(SampleEvent(value=i))

    threads = [threading.Thread(target=publish_many, args=(n * 50,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(received) == list(range(200))
