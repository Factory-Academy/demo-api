---
layout: default
title: Demo Moments
---

# Demo Moments Catalog

Available demo moments for this template:

## Code Review Bug Patterns

| Pattern | Best for | What Droid catches |
|---|---|---|
| SQL Injection | All industries | String interpolation in SQL query |
| PII Leak | Healthcare, Fintech | Logging sensitive data |
| Race Condition | Fintech, E-commerce | Check-then-act without locking |
| Decimal Precision | Fintech | Float arithmetic for money |
| Auth Bypass | DevTools, SaaS | Missing authentication check |
| Off-by-One | All | Pagination boundary error |

## Bug Fix Patterns

- Null reference (missing record check)
- Wrong calculation (discount logic error)
- Incorrect state transition (no validation)

## Refactoring Target

`src/utils/helpers.py` -- planted with 6 code smells (duplication, poor naming, magic numbers, deep nesting, long function, mixed concerns).

## Mission Templates

| Industry | Feature | Files created |
|---|---|---|
| Healthcare | Discharge summary | 4 new files |
| Fintech | Transaction reconciliation | 4 new files |
| E-commerce | Order fulfillment | 4 new files |
| DevTools | Webhook processing | 4 new files |
