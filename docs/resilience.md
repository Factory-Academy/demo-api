# Resilience utilities (`src/utils/resilience`)

Retry-with-backoff and a circuit breaker for calls to flaky or slow
dependencies (notification services, third-party APIs, anything over a
network). Everything is synchronous and dependency-free; the per-attempt
timeout is the only piece that uses a worker thread.

## Concepts

- **BackoffPolicy** — computes the delay between attempts. Delays grow
  exponentially (`base_delay * factor ** (attempt - 1)`), are clamped to
  `max_delay`, and get optional *equal jitter* (half the delay plus a random
  amount up to the other half) so many callers do not retry in lockstep.
- **RetryPolicy** — declarative config for `retry_call`: `max_attempts`, a
  `BackoffPolicy`, the `retryable_exceptions` tuple, and an optional per-attempt
  `timeout` (seconds).
- **CircuitBreaker** — trips to `OPEN` after a burst of consecutive failures,
  rejects calls while open, then allows limited probe calls (`HALF_OPEN`) once
  `recovery_timeout` elapses.
- **retry_call** — runs a callable under a policy and an optional breaker.
- **resilient** — a decorator wrapping `retry_call` around a function.

## Usage

```python
from src.utils.resilience import RetryPolicy, BackoffPolicy, CircuitBreaker, retry_call

policy = RetryPolicy(
    max_attempts=3,
    backoff=BackoffPolicy(base_delay=0.1, factor=2.0, max_delay=5.0),
    retryable_exceptions=(ConnectionError,),
    timeout=2.0,
)
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

result = retry_call(client.fetch, "/status", policy=policy, circuit_breaker=breaker)
```

Decorator form (the breaker instance is shared across every call):

```python
from src.utils.resilience import resilient, RetryPolicy, CircuitBreaker

@resilient(policy=RetryPolicy(max_attempts=4), circuit_breaker=CircuitBreaker())
def fetch_status(path: str) -> dict:
    ...
```

## Guarantees and edge cases

- **Retryable vs fatal** — only `retryable_exceptions` trigger another attempt.
  Anything else propagates immediately, without consuming attempts or tripping
  the breaker.
- **Exhaustion** — when every attempt fails, `retry_call` raises `RetryError`.
  The last underlying error is on `RetryError.last_error` and is chained with
  `raise ... from`, so the original traceback survives.
- **Per-attempt timeout** — a `timeout` bounds each attempt even if the callable
  never returns; it surfaces as `CallTimeoutError`, which is always treated as
  retryable (so a slow attempt is retried regardless of the policy's exception
  list).
- **Open breaker** — a call rejected by an open breaker raises
  `CircuitBreakerOpenError` *without invoking the callable*;
  `error.retry_after` reports the seconds until a probe is allowed.
- **Consecutive-failure counting** — the breaker counts consecutive failures;
  a single success while closed resets the counter.
- **Half-open probing** — after `recovery_timeout`, a limited number of probe
  calls are admitted. A probe success closes the breaker; a probe failure
  reopens it.
- **Thread-safe** — breaker state transitions are guarded by a re-entrant lock,
  and `time_func`/`rng`/`sleep` are injectable so tests stay deterministic.
- **Validation** — invalid configuration (`max_attempts < 1`, non-positive
  `timeout`, empty `retryable_exceptions`, bad backoff or breaker thresholds)
  raises `ValueError` at construction time.

## How it's wired into the app

`src/clients/status_notifier.py` posts item status changes to an external
notification service. Its single outbound call (`StatusNotifier.notify`) wraps
the transport in `retry_call` with a retry policy and a circuit breaker, so a
flaky or down dependency degrades gracefully instead of blocking the request
path:

```python
from src.clients.status_notifier import StatusNotifier

notifier = StatusNotifier(transport)       # transport(path, payload) -> dict
notifier.notify(item_id=1, status="active")
notifier.circuit_state                       # CircuitState.CLOSED / OPEN / HALF_OPEN
```

Transport failures raise `UpstreamError` (the only retryable error for the
notifier); any other exception propagates unchanged.

## Tests

- `tests/test_resilience.py` — unit coverage for backoff, retry, timeout, the
  circuit breaker, and the decorator (standard library only; a `FakeClock` and
  a recording `sleep` keep timing deterministic).
- `tests/test_status_notifier.py` — integration coverage proving the client
  retries transient `UpstreamError`s, surfaces fatal errors, and opens its
  breaker under sustained failure.

Run with `pytest tests/ -v`.
