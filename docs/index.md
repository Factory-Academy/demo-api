---
layout: default
title: Home
---

# Demo API Template (Python FastAPI)

SE reference hub for the `demo-api` template repository.

## What is this?

A minimal Python FastAPI application used as a starting point for personalized Factory AI sales demos. The code includes generic models (`Item`, `Widget`) that get renamed to domain-specific models during demo prep (e.g., `Patient`, `Appointment` for healthcare).

## Quick Links

- [Demo Flow](demo-flow) -- 15-min and quick demo timelines
- [Customization](customization) -- All `{{MARKER}}` replacement points
- [Demo Moments](moments) -- Available demo moments with code examples
- [Setup Guide](setup) -- How to run `/demo-setup`

## Tech Stack

- Python 3.9+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- pytest

## Running Locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

API docs at `http://localhost:8000/docs`.
