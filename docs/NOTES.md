---
layout: default
title: Module Notes
---

# Module Documentation

## `src/services/retry.py`

**Purpose:** Provides a generic retry utility for handling transient failures in function calls.

**Key Functions:**

- `retry(func, max_attempts=3)` — Attempts to execute a callable up to `max_attempts` times, returning the result on success. If all attempts fail, raises the last exception encountered.

**Usage:**

```python
from src.services.retry import retry

def call_api():
    # API call that might fail transiently
    return requests.get("https://api.example.com/data")

result = retry(call_api, max_attempts=3)
```

**Design Notes:**

- Accepts any callable with no arguments; use lambda or partial functions for parameterized calls
- Retries on all exceptions (no distinction between transient and permanent failures)
- Raises `ValueError` if `max_attempts < 1`
- Suitable for handling temporary network issues, rate limits, or timeouts

**Testing:** See `tests/test_retry.py` for coverage of success after retry and max attempt exhaustion.
