# demo-api

A Python FastAPI template repo used by the [demo-prep](https://github.com/Factory-Academy/demo-creation-skill) skill to generate personalized Factory AI sales demos.

**This is not a real application.** It's a minimal skeleton designed to be cloned, customized with prospect-specific domain models, and used as the backdrop for a 10-15 minute live demo of Factory's Droid.

## How this repo gets used

1. An SE runs `/demo-prep` in Droid and provides a prospect company name
2. The skill researches the prospect's industry and tech stack
3. It creates a branch (`demo/{company}-{date}`) off this repo
4. Generic code (`Item`, `Widget`) is replaced with domain-specific models (`Patient`, `Appointment` for healthcare; `Transaction`, `Account` for fintech; etc.)
5. Demo moments are planted — subtle bugs for code review, vague Linear tickets for spec mode, service files with no tests
6. A draft PR is opened so Droid can review it live during the demo

The main branch stays untouched. All customization happens on ephemeral demo branches.

## What's in here

| Path | Purpose |
|---|---|
| `src/main.py` | FastAPI entry point — registers routes, sets app title/description |
| `src/models/item.py` | Primary model (gets renamed to prospect's domain model) |
| `src/models/widget.py` | Secondary model (gets renamed to a related model) |
| `src/routes/item_routes.py` | CRUD endpoints for the primary model |
| `src/routes/widget_routes.py` | CRUD endpoints for the secondary model |
| `src/services/item_service.py` | Business logic — priority calculation, validation, batch updates |
| `tests/test_items.py` | Basic test coverage |
| `.factory/AGENTS.md` | Droid coding instructions |

## Customization markers

Files contain `{{MARKER}}` placeholders that the demo-prep skill replaces at branch creation time:

| Marker | Replaced with | Example |
|---|---|---|
| `{{COMPANY_NAME}}` | Prospect company | Acme Health |
| `{{PROJECT_DESCRIPTION}}` | Domain-specific description | Patient management platform |
| `{{DOMAIN_MODEL}}` | Primary model name | Patient |
| `{{DOMAIN_MODEL_LOWER}}` | Lowercase model name | patient |
| `{{DOMAIN_MODEL_PLURAL}}` | Plural model name | patients |
| `{{DOMAIN_MODELS}}` | All model names | Patient, Appointment |
| `{{INDUSTRY}}` | Prospect industry | Healthcare |
| `{{COMPANY_SLUG}}` | URL-safe company name | acme-health |

Files and classes are also renamed: `item.py` becomes `patient.py`, `class Item` becomes `class Patient`, and all imports are updated.

## Running locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

API docs at http://localhost:8000/docs. Tests: `pytest tests/ -v`.

## Persistent reviewed branch

The `demo/reviewed-example` branch has a draft PR ([#1](../../pull/1)) with pre-written review comments showing what Droid's code review looks like. SEs use this as a fallback if the live PR hasn't been reviewed yet.

## Related repos

- [demo-web-app](https://github.com/Factory-Academy/demo-web-app) — Next.js/React/TypeScript template
- [demo-cli](https://github.com/Factory-Academy/demo-cli) — TypeScript CLI template
- [demo-creation-skill](https://github.com/Factory-Academy/demo-creation-skill) — The skill that orchestrates all of this
