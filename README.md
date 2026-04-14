# {{COMPANY_NAME}} — {{PROJECT_DESCRIPTION}}

A FastAPI application for managing {{DOMAIN_MODEL_LOWER}} data in the {{INDUSTRY}} domain.

## Domain Models

{{DOMAIN_MODELS}}

## Quick Start

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

## API Endpoints

- `GET /{{DOMAIN_MODEL_PLURAL}}` — List all {{DOMAIN_MODEL_PLURAL}}
- `GET /{{DOMAIN_MODEL_PLURAL}}/{id}` — Get {{DOMAIN_MODEL_LOWER}} by ID
- `POST /{{DOMAIN_MODEL_PLURAL}}` — Create a new {{DOMAIN_MODEL_LOWER}}
- `PUT /{{DOMAIN_MODEL_PLURAL}}/{id}` — Update a {{DOMAIN_MODEL_LOWER}}
- `DELETE /{{DOMAIN_MODEL_PLURAL}}/{id}` — Delete a {{DOMAIN_MODEL_LOWER}}

## Project Structure

```
src/
  main.py          # FastAPI application entry point
  models/          # Data models
  routes/          # API route handlers
  services/        # Business logic
tests/             # Test suite
```

## Running Tests

```bash
pytest tests/ -v
```
