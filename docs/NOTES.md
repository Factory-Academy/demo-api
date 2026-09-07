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
- `retry()` helper function for fault tolerance (now a thin wrapper over the
  resilience module below, preserved for backwards compatibility)
- Pure functions for scoring and validation (easy to unit test)

## Resilience Module (`src/utils/resilience.py`)

Outbound calls (HTTP clients, database drivers, queues) fail transiently:
timeouts, dropped connections, brief 5xx spikes. The resilience module packages
the three standard mitigations so any client can reuse them instead of
hand-rolling retry loops.

### Building Blocks

- **`BackoffPolicy`**: exponential backoff (`base_delay * multiplier ** attempt`,
  capped at `max_delay`) with optional full jitter to avoid a thundering herd.
- **`CircuitBreaker`**: thread-safe breaker with `CLOSED → OPEN → HALF_OPEN`
  states. It trips open after `failure_threshold` consecutive failures, rejects
  calls for `recovery_timeout` seconds, then allows a limited number of trial
  calls before closing again.
- **`retry_with_backoff` / `resilient`**: retry a callable, optionally under a
  per-attempt `timeout` and behind a shared `CircuitBreaker`. A function form
  and a decorator form are provided.

### Error Model

- `RetryError` — every attempt failed transiently; the triggering error is on
  `.last_exception`.
- `CircuitBreakerOpenError` — the breaker rejected the call (never retried).
- `ResilienceTimeoutError` — an attempt exceeded its timeout (retryable).

Only exceptions listed in `retry_on` count as transient; anything else
propagates immediately without retrying or tripping the breaker.

### Testability

All timing and randomness is injectable — `sleep`, `clock`, and `random_fn` —
so the full behavior (backoff schedule, breaker state transitions, jitter
bounds) is verified deterministically without real delays.

## Status Notifier Client (`src/clients/status_notifier.py`)

`StatusNotifier` is the first client wired to the resilience module. It pushes
status changes to a downstream webhook and wraps that call with
retry-with-backoff plus a circuit breaker. Timeouts, connection errors, and 5xx
responses are treated as transient (retried, count against the breaker); 4xx
responses are permanent and fail fast. The transport is injectable via `sender`
so it can be tested offline.

`ItemService.batch_update_status` uses it: after a record's status is committed
locally, the change is announced downstream on a best-effort basis. A notifier
outage never fails the batch — affected IDs are reported under a `notify_failed`
key so callers can reconcile later.

### Why It Matters for Demos

The resilience module and notifier client extend the "domain expertise" story
into the integration layer: realistic third-party calls with retry, backoff,
timeout, and circuit-breaking that prospects recognize from their own stacks.
They make good targets for code review (edge cases, error mapping) and for
feature requests that add or harden an external integration.
