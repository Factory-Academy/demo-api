# Documentation Notes

## Module: `src/services/item_service.py`

The `ItemService` module handles core business logic for item management within the application. Its primary responsibilities include:

- **Priority Calculation**: Determines item priority (critical, high, medium, low) based on age, urgency, and criticality markers.
- **Validation**: Enforces business rules for item data, such as requiring names and ensuring dates are valid and in the future.
- **Batch Operations**: Manages bulk updates to item statuses with detailed result reporting.

## Design Spike: Pluggable Priority Strategies

### Goal

Priority scoring was a single hard-coded block inside `ItemService`. This spike
pulls that logic behind a small `PriorityStrategy` protocol with a factory, so
the scoring policy can be swapped (by config, request, or test) without touching
the call site.

### Shape

`src/services/priority/`

- `base.py` — `PriorityLevel` (ordered enum), `PriorityContext` (normalized,
  timezone-aware view of an item with an injectable `now`), `PriorityResult`
  (level + score + human-readable `reasons`), and the `PriorityStrategy`
  `Protocol`.
- `strategies.py` — two implementations (below).
- `factory.py` — `create_priority_strategy(name, **kwargs)` plus a name registry
  with `register_strategy` / `available_strategies`.

`ItemService` takes an optional `priority_strategy` and defaults to the factory,
so existing behavior is unchanged while the policy is now injectable.

### The two approaches

**`WeightedScoreStrategy` (additive score).** The original model, generalized:
`urgency * 10`, `+50` when critical, `+0.5` per day once older than 30 days,
then 80/50/20 cut-offs. All weights and thresholds are constructor arguments.

- *Strengths:* dimensionless and composable — any number of signals can be
  summed; tuning is a matter of weights; no deadline data required.
- *Weaknesses:* the number is hard to interpret ("what does 72 mean?"); a high
  urgency can mask an item that is due in an hour; cut-offs need calibration.

**`DeadlineStrategy` (SLA / time-to-due).** Buckets items by how soon they are
due: overdue is always critical, otherwise windows of `<=1 / <=3 / <=7` days map
to critical/high/medium, with an optional one-level bump for critical items.

- *Strengths:* directly models "what will breach first," which is what an
  operator usually wants; easy to explain; windows map to real SLAs.
- *Weaknesses:* useless without a due date (falls back to a criticality-only
  guess); ignores accumulated urgency; a cliff at each window boundary.

### Recommendation

Default to `WeightedScoreStrategy` for backward compatibility. Prefer
`DeadlineStrategy` for workloads with real SLAs/due dates. Because selection is
behind the factory, a deployment can choose per environment, and a future hybrid
(score feeding the deadline buckets, or vice versa) is just another registered
strategy — no call-site changes.

### Follow-ups if promoted beyond a spike

- Persist the chosen strategy name in config and wire it into the routes.
- If evaluation becomes hot, wrap it with the existing `ttl_cache`; `now` is
  injectable, so results stay deterministic and cacheable.
- Surface `PriorityResult.reasons` in an API response or admin view for
  explainability.
