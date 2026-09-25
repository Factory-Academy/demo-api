# Feature Flags

This project includes a lightweight, environment-driven feature flag system for enabling/disabling features dynamically.

## Quick Start

### Basic Usage

```python
from src.utils.feature_flags import flags

# Check if a feature is enabled
if flags.is_enabled("my_feature"):
    # Feature is enabled
    pass
```

### Environment Variables

Feature flags are controlled via environment variables with the prefix `FEATURE_`. For example:

```bash
# Enable a feature
export FEATURE_MY_FEATURE=true

# Disable a feature (or leave unset)
export FEATURE_MY_FEATURE=false
```

A flag is considered **enabled** if its environment variable is set to one of:
- `true` (case-insensitive)
- `1`
- `yes` (case-insensitive)

All other values (including missing variables) are treated as **disabled**.

## Protecting Endpoints

Use the `@flags.require_flag()` decorator to make an endpoint require a feature flag:

```python
from fastapi import APIRouter
from src.utils.feature_flags import flags

router = APIRouter()

@router.get("/new-feature")
@flags.require_flag("new_feature")
async def new_feature_endpoint():
    return {"status": "new feature enabled"}
```

If the flag is disabled, the endpoint returns HTTP 403 Forbidden.

### Example

Enable the feature:
```bash
export FEATURE_NEW_FEATURE=true
```

Call the endpoint:
```bash
curl http://localhost:8000/new-feature
# {"status": "new feature enabled"}
```

Disable the feature:
```bash
unset FEATURE_NEW_FEATURE
```

Call the endpoint again:
```bash
curl http://localhost:8000/new-feature
# {"detail": "Feature not enabled"}
```

## Advanced Usage

### Custom Prefix

Create a feature flag instance with a custom environment variable prefix:

```python
from src.utils.feature_flags import FeatureFlags

my_flags = FeatureFlags(prefix="MY_APP_")

# This will check MY_APP_FEATURE_NAME
my_flags.is_enabled("feature_name")
```

### Clear Cache (Testing)

Feature flags are cached after their first check for performance. In tests, clear the cache:

```python
from src.utils.feature_flags import flags

flags.clear_cache()
```

## Current Integrations

The following features are currently protected by flags:

- **`FEATURE_ITEM_STATS`**: Enables the `/items/stats/summary` endpoint that returns item statistics.

## Testing

See `tests/test_feature_flags.py` for comprehensive test examples including:
- Enabling/disabling flags
- Testing decorated endpoints
- Clearing cache in tests
- Custom prefixes

Run tests with:
```bash
pytest tests/test_feature_flags.py -v
```
