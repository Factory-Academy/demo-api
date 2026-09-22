# Feature flag helper notes

This prototype adds an env-driven feature flag helper at `src/utils/feature_flags.py`.

## Interface

- Use `feature_flags.is_enabled("<flag_name>", default=False)` to check a flag.
- Flag names are normalized to uppercase with `-` converted to `_`.
- Environment variable format is `FEATURE_<FLAG_NAME>`.

Example:

- `feature_flags.is_enabled("widgets-v2-api")` reads `FEATURE_WIDGETS_V2_API`.

Truthy values: `1`, `true`, `yes`, `on`, `enabled`  
Falsy values: `0`, `false`, `no`, `off`, `disabled`

Unknown values fall back to the provided `default`.

## Integration in this prototype

The existing `/health` path now accepts `include_flags=true`.  
When enabled, it returns a `feature_flags` object including `widgets_v2_api`.
