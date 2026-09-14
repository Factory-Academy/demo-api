# Resilience utilities: retry-with-backoff + circuit breaker

`src/utils/resilience/` provides a small, dependency-free toolkit for calling
flaky external services. It combines three pieces:

- **`BackoffPolicy`** (`backoff.py`) — exponential backoff with an optional
  "equal jitter" spread so many callers don't retry in lockstep.
- **`CircuitBreaker`** (`circuit_breaker.py`) — a thread-safe breaker with the
  usual `CLOSED → OPEN → HALF_OPEN` lifecycle.
- **`retry_call` / `resilient`** (`retry.py`) — the glue: retries retryable
  errors with backoff, enforces a per-attempt timeout, and consults an optional
  breaker.

Everything is exported from the package root:

```python
from src.utils.resilience import (
    BackoffPolicy, CircuitBreaker, RetryPolicy, retry_call, resilient,
)
```

## Quick start

```python
policy = RetryPolicy(
    max_attempts=3,
    backoff=BackoffPolicy(base_delay=0.1, factor=2.0, max_delay=5.0),
    retryable_exceptions=(TimeoutError, ConnectionError),
    timeout=2.0,           # seconds, per attempt
)
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

result = retry_call(client.fetch, "/status", policy=policy, circuit_breaker=breaker)
```

Or as a decorator:

```python
@resilient(policy=policy, circuit_breaker=breaker)
def fetch_status(path):
    ...
```

## Behavior and edge cases

- **What gets retried.** Only exceptions in `retryable_exceptions` (default:
  `Exception`) trigger another attempt. Anything else propagates immediately
  without consuming attempts or recording a breaker failure — so a
  non-transient bug (e.g. a `ValueError` on a malformed payload) fails fast.
- **Exhaustion.** When every attempt fails, `retry_call` raises `RetryError`.
  The final underlying exception is preserved on `RetryError.last_error` and
  chained via `raise ... from`, so the original traceback is not lost.
- **Timeouts.** A per-attempt `timeout` runs the callable on a worker thread and
  stops *waiting* after the deadline, raising `CallTimeoutError` (always
  retryable, even if you narrow `retryable_exceptions`). Python can't forcibly
  kill the thread, so a timed-out call keeps running in the background; treat
  `CallTimeoutError` as "result unknown," which is why the helper only wraps
  idempotent-ish calls in the client below.
- **Circuit breaker.** After `failure_threshold` consecutive failures the
  breaker opens and `retry_call` raises `CircuitBreakerOpenError` without
  invoking the callable. After `recovery_timeout` it moves to half-open and
  admits up to `half_open_max_calls` probes; a successful probe closes it, a
  failed probe reopens it. A success while closed resets the failure streak.
- **Jitter bounds.** With jitter on, the delay for an attempt lands in
  `[d/2, d]` where `d` is the capped exponential delay. Disable it
  (`jitter=False`) for deterministic tests.

## Testability

The pieces avoid real time so tests stay fast and deterministic:

- `retry_call(..., sleep=...)` — inject a no-op or recording sleep.
- `CircuitBreaker(time_func=...)` — inject a fake clock to advance time.
- `BackoffPolicy.compute_delay(attempt, rng=...)` — inject the jitter source.

See `tests/test_resilience.py` for the full matrix (backoff math, breaker state
transitions, timeout paths, and retry integration).

## Wiring

`src/clients/status_notifier.py` wires the utility into one outbound call.
`StatusNotifier.notify()` posts item status changes through an injected
transport, wrapped by `retry_call` with a breaker. Only `UpstreamError`
(transient transport failures) is retried; malformed responses fail fast. The
transport is a constructor argument, so the client is fully testable without a
network — see `tests/test_status_notifier.py`.
