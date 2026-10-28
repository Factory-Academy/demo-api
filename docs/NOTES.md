# Resilience utilities: retry-with-backoff + circuit breaker

This note documents `src/utils/resilience/` and how it is wired into the
status-notifier client.

## What it provides

| Component | File | Responsibility |
|---|---|---|
| `BackoffPolicy` | `backoff.py` | Exponential backoff with optional full jitter |
| `CircuitBreaker` / `CircuitBreakerConfig` | `circuit_breaker.py` | Three-state breaker (closed / open / half-open) |
| `RetryPolicy` / `retry_call` / `resilient` | `retry.py` | Retry runner and decorator combining the two above |
| `ResilienceError`, `RetryError`, `CircuitOpenError` | `errors.py` | Typed errors |

All of it is pure standard library, so it has no third-party dependencies and
is cheap to unit test.

## Usage

```python
from src.utils.resilience import (
    BackoffPolicy, CircuitBreaker, CircuitBreakerConfig, RetryPolicy, retry_call,
)

breaker = CircuitBreaker("payments", CircuitBreakerConfig(failure_threshold=3))
policy = RetryPolicy(
    max_attempts=4,
    backoff=BackoffPolicy(base_delay=0.05, max_delay=2.0),
    retry_on=(TimeoutError, ConnectionError),
)

result = retry_call(charge_card, amount, policy=policy, breaker=breaker)
```

Or as a decorator (the policy and breaker are shared across calls, so the
breaker accumulates state the way you want):

```python
from src.utils.resilience import resilient

@resilient(policy=policy, breaker=breaker)
def charge_card(amount): ...
```

## Design decisions

- **Full jitter.** With jitter enabled the delay is drawn uniformly from
  `[0, computed_delay]`. This spreads retries from many callers and avoids a
  synchronised "retry storm" against a recovering dependency.
- **The breaker only counts availability failures.** `retry_call` records a
  breaker failure only for exceptions the policy considers *retryable*. A
  non-retryable error (for example a 4xx translated into
  `NotifierRejectedError`, or a programming `ValueError`) propagates
  immediately and does **not** trip the breaker, because it says nothing about
  whether the dependency is up.
- **Half-open admission control.** When the recovery timeout elapses the
  breaker moves to half-open and admits a limited number of trial calls
  (`half_open_max_calls`). A success closes it; a single failure reopens it.
- **Injectable clock, sleep, and RNG.** The breaker takes a `clock`, and
  `retry_call` takes `sleep`, `clock`, and `rng`. Tests drive these with fakes,
  so the full retry/backoff/recovery behaviour is verified without real waiting.

## Edge cases handled

- **Timeouts.** Transient timeouts are retryable. `TimeoutError` is retryable
  by default, and the notifier client maps `httpx.TimeoutException` to its
  retryable `NotifierUnavailableError`.
- **Permanent failures.** Exceptions in `give_up_on` (or simply not in
  `retry_on`) are never retried, even if they also match `retry_on`.
- **Exhausted retries.** When every attempt fails, `retry_call` raises
  `RetryError` carrying the attempt count and the last underlying exception.
- **Open circuit mid-retry.** If a failure trips the breaker between attempts,
  the next attempt is rejected with `CircuitOpenError` before the function
  runs, so we stop hammering a dead dependency immediately.
- **Total time budget.** `RetryPolicy.deadline` caps the wall-clock time spent
  across all attempts; the final backoff is clamped so a retry never overruns
  the budget.

## Wiring: `StatusNotifierClient`

`src/clients/status_notifier.py` posts item status changes to an external
notifier service. Its single outbound call (`_send`) is wrapped with
`retry_call(..., policy=..., breaker=...)`:

- `httpx` timeouts / connection errors / 5xx -> `NotifierUnavailableError`
  (retried, counts against the breaker).
- 4xx -> `NotifierRejectedError` (not retried, does not trip the breaker).

Delivery is **best-effort**: `notify_status_change` returns `True`/`False` and
never raises for an expected notifier failure, so a down notifier can't break
the local operation that triggered it.

`ItemService.batch_update_status` (`src/services/item_service.py`) accepts an
optional `notifier`. When present, each successful status change is pushed
through the client, and the batch result gains a `notified` list recording
which changes were delivered. When no notifier is configured the service
behaves exactly as before.

## Tests

- `tests/utils/test_resilience.py` — backoff growth/cap/jitter bounds/validation;
  breaker open/half-open/close/reopen/reset and admission limits; retry success,
  recovery, exhaustion, non-retryable propagation, `give_up_on` precedence,
  deadline budget, breaker integration, and the decorator.
- `tests/test_status_notifier.py` — client behaviour over `httpx.MockTransport`:
  success, 5xx retry-then-succeed, persistent 5xx, 4xx no-retry, timeout retry,
  circuit open drops calls, and recovery after the timeout.
- `tests/services/test_item_service_notify.py` — the service wiring, including
  skipped/missing records and dropped deliveries.

> Environment note: the checked-in `venv`/`testenv` in this repo are stripped
> down (no runnable `httpx`/`pytest`), so the suite is written for a normal
> `pip install -r requirements.txt` environment. The pure-stdlib resilience
> tests and the service-wiring tests were validated here directly with
> `python3`; the `httpx`-based client tests require a full install to run.
