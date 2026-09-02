# Feature flag helper notes

Added a small env-driven feature flag helper at `src/feature_flags.py`.

## Interface

- Use `is_feature_enabled("<FLAG_NAME>", default=False)` for simple checks.
- Flags map to environment variables with a `FEATURE_` prefix.
  - Example: `is_feature_enabled("ITEMS_FORCE_INACTIVE_STATUS")`
  - Reads: `FEATURE_ITEMS_FORCE_INACTIVE_STATUS`
- Truthy values: `1`, `true`, `yes`, `on`, `enabled`
- Falsy values: `0`, `false`, `no`, `off`, `disabled`
- Missing or unrecognized values fall back to `default`.

## Current integration

`src/routes/item_routes.py` now checks `FEATURE_ITEMS_FORCE_INACTIVE_STATUS` during item creation.  
When enabled, newly created items are forced to `status="inactive"`.
