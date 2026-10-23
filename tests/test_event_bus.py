import threading

import pytest

from src.events import (
    AuditLog,
    Event,
    EventBus,
    ItemCreated,
    ItemDeleted,
    ItemUpdated,
    get_event_bus,
)


@pytest.fixture
def bus():
    return EventBus()


def make_created(item_id=1, name="Sample", status="active"):
    return ItemCreated(item_id=item_id, name=name, status=status)


# --- subscribe / publish basics -------------------------------------------


def test_publish_invokes_subscribed_handler(bus):
    received = []
    bus.subscribe(ItemCreated, received.append)

    count = bus.publish(make_created(item_id=7))

    assert count == 1
    assert received[0].item_id == 7


def test_publish_with_no_subscribers_is_a_noop(bus):
    assert bus.publish(make_created()) == 0


def test_multiple_handlers_all_receive_event_in_registration_order(bus):
    order = []
    bus.subscribe(ItemCreated, lambda e: order.append("first"))
    bus.subscribe(ItemCreated, lambda e: order.append("second"))

    bus.publish(make_created())

    assert order == ["first", "second"]


def test_handlers_only_receive_their_event_type(bus):
    created, deleted = [], []
    bus.subscribe(ItemCreated, created.append)
    bus.subscribe(ItemDeleted, deleted.append)

    bus.publish(make_created())

    assert len(created) == 1
    assert deleted == []


# --- typed dispatch across the event hierarchy -----------------------------


def test_subscribing_to_base_event_receives_every_event(bus):
    seen = []
    bus.subscribe(Event, seen.append)

    bus.publish(make_created())
    bus.publish(ItemUpdated(item_id=1, changed_fields=("name",)))
    bus.publish(ItemDeleted(item_id=1))

    assert [e.event_name for e in seen] == ["ItemCreated", "ItemUpdated", "ItemDeleted"]


def test_base_and_specific_handlers_both_fire(bus):
    calls = []
    bus.subscribe(Event, lambda e: calls.append("base"))
    bus.subscribe(ItemCreated, lambda e: calls.append("specific"))

    invoked = bus.publish(make_created())

    assert invoked == 2
    assert set(calls) == {"base", "specific"}


# --- validation / error cases ----------------------------------------------


def test_publishing_a_non_event_raises_type_error(bus):
    with pytest.raises(TypeError):
        bus.publish({"item_id": 1})


def test_subscribing_non_event_type_raises_type_error(bus):
    with pytest.raises(TypeError):
        bus.subscribe(dict, lambda e: None)


def test_subscribing_non_callable_raises_type_error(bus):
    with pytest.raises(TypeError):
        bus.subscribe(ItemCreated, "not-callable")


# --- handler isolation ------------------------------------------------------


def test_failing_handler_does_not_block_other_handlers(bus):
    survived = []

    def boom(_event):
        raise RuntimeError("handler failure")

    bus.subscribe(ItemCreated, boom)
    bus.subscribe(ItemCreated, survived.append)

    invoked = bus.publish(make_created())

    assert invoked == 2
    assert len(survived) == 1


def test_errors_are_routed_to_custom_error_handler():
    errors = []
    bus = EventBus(on_error=lambda event, handler, exc: errors.append((event.event_name, str(exc))))

    def boom(_event):
        raise ValueError("nope")

    bus.subscribe(ItemCreated, boom)
    bus.publish(make_created())

    assert errors == [("ItemCreated", "nope")]


# --- unsubscribe ------------------------------------------------------------


def test_unsubscribe_stops_delivery(bus):
    received = []
    bus.subscribe(ItemCreated, received.append)
    bus.unsubscribe(ItemCreated, received.append)

    bus.publish(make_created())

    assert received == []


def test_unsubscribe_unknown_handler_returns_false(bus):
    assert bus.unsubscribe(ItemCreated, lambda e: None) is False


def test_subscription_handle_unsubscribes(bus):
    received = []
    sub = bus.subscribe(ItemCreated, received.append)

    assert sub.active is True
    assert sub.unsubscribe() is True
    assert sub.active is False
    assert sub.unsubscribe() is False  # idempotent

    bus.publish(make_created())
    assert received == []


def test_subscription_as_context_manager(bus):
    received = []
    with bus.subscribe(ItemCreated, received.append):
        bus.publish(make_created())
    bus.publish(make_created())

    assert len(received) == 1


def test_duplicate_subscribe_is_idempotent(bus):
    received = []
    bus.subscribe(ItemCreated, received.append)
    bus.subscribe(ItemCreated, received.append)

    bus.publish(make_created())

    assert len(received) == 1
    assert bus.subscriber_count(ItemCreated) == 1


# --- subscribe_once ---------------------------------------------------------


def test_subscribe_once_fires_exactly_once(bus):
    received = []
    bus.subscribe_once(ItemCreated, received.append)

    bus.publish(make_created())
    bus.publish(make_created())

    assert len(received) == 1
    assert bus.subscriber_count(ItemCreated) == 0


def test_subscribe_once_is_removed_even_when_it_raises(bus):
    def boom(_event):
        raise RuntimeError("fail once")

    bus.subscribe_once(ItemCreated, boom)
    bus.publish(make_created())  # error is isolated

    assert bus.subscriber_count(ItemCreated) == 0


# --- re-entrant handlers ----------------------------------------------------


def test_handler_may_unsubscribe_itself_during_publish(bus):
    received = []

    def handler(event):
        received.append(event)
        bus.unsubscribe(ItemCreated, handler)

    bus.subscribe(ItemCreated, handler)
    bus.publish(make_created())
    bus.publish(make_created())

    assert len(received) == 1


def test_handler_may_subscribe_a_new_handler_during_publish(bus):
    late = []

    def adder(_event):
        bus.subscribe(ItemCreated, late.append)

    bus.subscribe(ItemCreated, adder)
    bus.publish(make_created())  # adder registers late, but not for this publish
    assert late == []

    bus.publish(make_created())
    assert len(late) == 1


# --- counts and clearing ----------------------------------------------------


def test_subscriber_count_total_and_by_type(bus):
    bus.subscribe(ItemCreated, lambda e: None)
    bus.subscribe(ItemDeleted, lambda e: None)

    assert bus.subscriber_count(ItemCreated) == 1
    assert bus.subscriber_count(ItemDeleted) == 1
    assert bus.subscriber_count() == 2


def test_clear_single_type_leaves_others(bus):
    bus.subscribe(ItemCreated, lambda e: None)
    bus.subscribe(ItemDeleted, lambda e: None)

    bus.clear(ItemCreated)

    assert bus.subscriber_count(ItemCreated) == 0
    assert bus.subscriber_count(ItemDeleted) == 1


def test_clear_all(bus):
    bus.subscribe(ItemCreated, lambda e: None)
    bus.subscribe(ItemDeleted, lambda e: None)

    bus.clear()

    assert bus.subscriber_count() == 0


# --- event value semantics --------------------------------------------------


def test_events_are_immutable():
    event = make_created()
    with pytest.raises(Exception):
        event.item_id = 999  # frozen dataclass


def test_event_name_and_to_dict():
    event = make_created(item_id=3, name="Gadget", status="active")

    assert event.event_name == "ItemCreated"
    assert event.name == "Gadget"  # payload field, independent of event_name
    payload = event.to_dict()
    assert payload["item_id"] == 3
    assert payload["name"] == "Gadget"
    assert "occurred_at" in payload


# --- thread safety ----------------------------------------------------------


def test_concurrent_publishes_deliver_every_event(bus):
    received = []
    lock = threading.Lock()

    def handler(event):
        with lock:
            received.append(event.item_id)

    bus.subscribe(ItemCreated, handler)

    def worker(start):
        for i in range(start, start + 100):
            bus.publish(make_created(item_id=i))

    threads = [threading.Thread(target=worker, args=(base,)) for base in (0, 1000, 2000)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(received) == 300


# --- audit subscriber -------------------------------------------------------


def test_audit_log_captures_all_events(bus):
    audit = AuditLog()
    audit.attach(bus)

    bus.publish(make_created(item_id=1))
    bus.publish(ItemDeleted(item_id=1))

    assert audit.names() == ["ItemCreated", "ItemDeleted"]
    assert audit.entries[0].payload["item_id"] == 1


def test_audit_log_detach_stops_recording(bus):
    audit = AuditLog()
    audit.attach(bus)
    audit.detach()

    bus.publish(make_created())

    assert audit.entries == []


def test_audit_attach_is_idempotent(bus):
    audit = AuditLog()
    audit.attach(bus)
    audit.attach(bus)

    assert bus.subscriber_count(Event) == 1


# --- default bus ------------------------------------------------------------


def test_get_event_bus_returns_singleton():
    assert get_event_bus() is get_event_bus()
