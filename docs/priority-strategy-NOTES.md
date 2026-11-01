# Pluggable priority strategies

This note documents `src/services/priority/` and how it is wired into
`ItemService`. (The existing `docs/NOTES.md` covers the unrelated resilience
utilities.)

## What it provides

| Component | File | Responsibility |
|---|---|---|
| `PriorityLevel`, `PriorityInput`, `PriorityAssessment` | `models.py` | Shared value types: ordered level enum, normalised input, uniform result |
| `PriorityStrategy` | `protocol.py` | The strategy contract, a `typing.Protocol` |
| `WeightedScoreStrategy` / `WeightedScoreConfig` | `weighted.py` | Weighted-sum heuristic (urgency + critical flag + age) |
| `SlaDeadlineStrategy` / `SlaDeadlineConfig` | `sla.py` | Time-to-deadline heuristic |
| `create_priority_strategy`, `register_strategy`, `available_strategies` | `factory.py` | Name → strategy registry/factory |
| `PriorityError`, `UnknownStrategyError` | `errors.py` | Typed errors |

It is pure standard library, so it has no third-party dependencies and is cheap
to unit test.

## Usage

```python
from src.services.priority import PriorityInput, create_priority_strategy

strategy = create_priority_strategy("sla")               # or "weighted" / "default"
assessment = strategy.assess(PriorityInput.from_item(item))
assessment.level   # PriorityLevel.HIGH  (== "high")
assessment.score   # strategy-specific diagnostic number
assessment.reason  # short human-readable explanation
```

Through the service, which defaults to the weighted strategy:

```python
service = ItemService(db, priority_strategy=create_priority_strategy("sla"))
service.calculate_priority(item)  # -> "critical"  (plain string, as before)
service.assess_priority(item)     # -> full PriorityAssessment
```

## Why a protocol + factory (the "spike" shape)

- **`Protocol` over an ABC.** Strategies conform *structurally*: anything with a
  `name` and an `assess(PriorityInput) -> PriorityAssessment` satisfies the
  contract, with no base class to inherit. Test doubles and third-party
  strategies stay boilerplate-free, and `@runtime_checkable` still lets us
  `isinstance`-check at the boundary. The cost is that the protocol is only
  enforced by a static checker plus the shallow runtime check, not by
  inheritance.
- **Factory over direct construction.** Call sites name a strategy
  (`"weighted"`, `"sla"`) instead of importing a concrete class, so selection
  can come from config and new strategies register without touching callers.
  `register_strategy` refuses to clobber an existing name unless `replace=True`,
  so an accidental duplicate fails loudly.
- **Normalise input once.** `PriorityInput.from_item` parses dates and fills
  defaults a single time, so each strategy works with clean typed fields rather
  than re-parsing the loosely-typed item dict. Malformed data raises
  `PriorityError` instead of scoring silently wrong.
- **Injectable clock.** Both strategies take a `clock`, so age- and
  deadline-based scoring is tested deterministically without real time, matching
  the pattern already used in `src/utils/resilience/`.

## Weighing the two strategies

| | Weighted score | SLA / deadline |
|---|---|---|
| Signal | Urgency, critical flag, age | Time until `due_date` |
| Needs a due date | No | Yes (falls back to a configurable level) |
| Best when | Importance is intrinsic to the item | Work is deadline-driven |
| Blind spot | Ignores deadlines entirely | Ignores intrinsic urgency except the critical bump |
| `score` meaning | The numeric score | Hours until due (negative = overdue) |
| Tuning | Weights + bucket thresholds | Hour windows + escalation toggle |

Neither dominates: the weighted strategy answers "how important is this?" while
the SLA strategy answers "how soon is this due?". Keeping both behind one
contract lets a deployment choose per its domain, and makes a future blended
strategy (e.g. `max` of the two levels) a drop-in third implementation rather
than a rewrite. The weighted strategy is the default because its defaults
reproduce the original inline `calculate_priority` scoring exactly, so existing
behaviour is unchanged.

## Edge cases handled

- **Missing `created_at`.** The old inline code did `item["created_at"]` and
  raised `KeyError`. The weighted strategy now treats a missing creation time as
  age 0 (brand new) instead of crashing.
- **Missing `due_date`.** The SLA strategy returns a configurable level
  (`LOW` by default) and a score of `+inf` meaning "no deadline pressure".
- **Future `created_at` / negative age.** Contributes no age score; never
  subtracts.
- **Overdue items.** Negative hours-remaining classify as `CRITICAL`, with the
  overdue amount reported in `reason`.
- **Critical escalation cap.** The SLA critical bump is capped at `CRITICAL`
  via `PriorityLevel.from_rank`, so it can't overflow past the top bucket.
- **Loosely-typed input.** `PriorityInput.from_item` accepts `datetime`,
  `date`, and ISO strings for dates and coerces a missing/`None` urgency to 0;
  an unparseable date or non-integer urgency raises `PriorityError`.
- **Bad configuration.** `WeightedScoreConfig` and `SlaDeadlineConfig` validate
  their weights/thresholds in `__post_init__`, so an inverted or negative
  configuration fails at construction rather than producing silent nonsense.
- **Unknown strategy name.** `create_priority_strategy` raises
  `UnknownStrategyError` carrying the list of registered names.

## Wiring: `ItemService`

`ItemService.__init__` gains an optional `priority_strategy`; when omitted it
defaults to `create_priority_strategy("weighted")`. `calculate_priority` keeps
its original `(item: dict) -> str` signature (it returns `assessment.level.value`,
a plain string), and a new `assess_priority` exposes the full assessment for
callers that want the score and reason. No other call site changes.

## Tests

- `tests/services/priority/test_models.py` — level ordering/escalation/clamping
  and `PriorityInput.from_item` parsing, defaults, and error cases.
- `tests/services/priority/test_weighted.py` — buckets, the critical bonus,
  age thresholds, missing/future `created_at`, and config validation.
- `tests/services/priority/test_sla.py` — overdue/soon/far buckets, the
  window boundary, missing due date, critical escalation (and disabling it),
  and config validation.
- `tests/services/priority/test_factory.py` — built-in registration, the
  `"default"` alias, protocol conformance, kwargs forwarding, custom
  registration, clobber protection, and unknown-name errors.
- `tests/services/priority/test_item_service_priority.py` — service wiring:
  legacy-scoring parity, plain-string return, `assess_priority`, the
  no-longer-raising missing `created_at`, and an injected SLA strategy.

> Environment note: the checked-in `venv`/`testenv` are stripped down (no
> runnable `pytest`), matching the note in `docs/NOTES.md`. This module and its
> tests are pure standard library; the logic and the legacy-scoring parity were
> validated here directly with `python3`. Run the suite with `pytest tests/ -v`
> in a normal `pip install -r requirements.txt` environment.
