# Rivian Fleet API

Fleet and vehicle management platform for Rivian's connected vehicle ecosystem.

## Domain Models

- **Vehicle** -- Tracks VIN, model, year, status, and customer association
- **ServiceAppointment** -- Service scheduling for fleet vehicles

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/vehicles/` | List all vehicles |
| GET | `/vehicles/{id}` | Get vehicle by ID |
| POST | `/vehicles/` | Register a new vehicle |
| PUT | `/vehicles/{id}` | Update vehicle details |
| DELETE | `/vehicles/{id}` | Remove a vehicle |
| GET | `/service-appointments/` | List service appointments |
| GET | `/service-appointments/{id}` | Get appointment by ID |
| POST | `/service-appointments/` | Schedule a service appointment |
| GET | `/health` | Health check |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

API docs at http://localhost:8000/docs

## Tests

```bash
pytest tests/ -v
```
