# Design notes: pluggable priority strategies

## Problem

`ItemService.calculate_priority` hard-coded a single scoring formula (an
additive point model with an urgency weight, a critical bonus, and an aging
bump). Different demo domains want different definitions of "urgent": a support
queue cares about how long a ticket has waited, while an operations queue cares
about how close a task is to its deadline. Baking one formula into the service
made that switch a code edit at every call site.

This spike extracts scoring behind a small strategy contract so the formula
becomes a configuration choice.

## Shape of the solution

```
src/services/priority/
  protocol.py     PriorityStrategy (Protocol), PriorityLevel, PriorityResult
  strategies.py   WeightedScoreStrategy, DeadlineAwareStrategy
  factory.py      create_priority_strategy(name, **options) + registry
  coerce.py       shared field normalization / edge-case handling
  errors.py       PriorityError hierarchy
  __init__.py     public surface
```

The contract is a single method:

```python
strategy.assess(item) -> PriorityResult(level, score, reason)
```

* `level` — a `PriorityLevel` enum (`str`-backed, so it serializes and compares
  as the plain strings the API already uses).
* `score` — a float for sorting. Every strategy uses the convention *higher =
  more urgent* so results are comparable and sortable regardless of source.
* `reason` — a human-readable trace for debugging and audit.

## The two strategies

### `WeightedScoreStrategy` (default)

Additive points: `urgency * weight (+ critical bonus)(+ aging past a grace
period)`, then bucketed against thresholds. Its defaults reproduce the original
`ItemService` behavior exactly, which the test suite pins with a regression
guard, so adopting it is a no-op.

* **Strengths** — cheap, explainable, tunable per weight; needs no due date.
* **Weaknesses** — the score is an abstract number, not a promise about *when*
  something happens; thresholds drift as you add signals; nothing guarantees an
  approaching deadline is respected.

### `DeadlineAwareStrategy`

SLA model: priority is a function of days remaining until `due_date`. Overdue
items are always critical; a `is_critical` flag pins to critical regardless of
deadline; items with no due date fall back to a configurable level (default
`LOW`).

* **Strengths** — directly answers "how soon must this be handled?"; ordering
  matches real-world deadlines; thresholds are intuitive (1/3/7 days).
* **Weaknesses** — useless without due dates; ignores accumulated importance
  (a low-value item due tomorrow outranks a high-value item due next week).

## Why a factory + registry

Call sites ask for a strategy *by name* (`create_priority_strategy("deadline")`)
rather than importing a concrete class. That keeps the selection in one place
and lets it come from config, a request parameter, or a feature flag.
`register_strategy` lets a demo branch add a domain-specific strategy without
editing the package, and `**options` are forwarded to constructors for
per-deployment tuning. Unknown names raise `UnknownStrategyError` listing what
is available, which fails loudly instead of silently defaulting.

## Edge-case handling

Field coercion lives in `coerce.py` so both strategies behave identically at the
boundaries:

* `created_at` / `due_date` accept native datetimes or ISO-8601 strings
  (including a trailing `Z`); naive values are assumed UTC to match the app's
  `datetime.utcnow()` writes.
* A `created_at` in the future (clock skew) clamps aging to zero, so time can
  never *lower* an item's priority.
* `urgency` accepts numbers or numeric strings; a non-numeric value raises
  `InvalidItemError` with the offending field rather than leaking a `TypeError`
  mid-calculation.
* Missing fields fall back to safe defaults (`urgency=0`, age `0`, no deadline).

## Trade-offs and alternatives considered

* **`Protocol` vs `ABC`.** A `runtime_checkable` `Protocol` lets any duck-typed
  object (including the test's inline `AlwaysCritical`) satisfy the contract
  without inheriting from our base. That fits a pluggable spike better than an
  ABC, at the cost of `isinstance` only checking method *names*, not signatures.
* **Instance-per-lookup vs singletons.** Strategies are stateless, so the
  registry stores zero-arg-friendly constructors and hands back a fresh instance
  each call. This keeps `**options` tuning simple; if allocation ever mattered
  we could memoize the default-option instances.
* **Returning a rich `PriorityResult` vs a bare string.** The service still
  exposes a string label for backward compatibility, but internally we carry
  score and reason so future call sites can sort and explain decisions.

## Follow-ups if productionized

* Config-driven default strategy and thresholds instead of code defaults.
* A composite strategy (e.g. `max(weighted, deadline)`) for queues that care
  about both importance and deadlines.
* Property-based tests over the coercion layer.
