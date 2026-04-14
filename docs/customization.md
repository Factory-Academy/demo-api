---
layout: default
title: Customization
---

# Customization Markers

All replacement points in the template:

| Marker | Replaced with | Example |
|---|---|---|
| `{{COMPANY_NAME}}` | Prospect company name | "Acme Health" |
| `{{COMPANY_SLUG}}` | URL-safe company name | "acme-health" |
| `{{PROJECT_DESCRIPTION}}` | Domain-specific description | "Patient management platform" |
| `{{DOMAIN_MODEL}}` | Primary model name (singular) | "Patient" |
| `{{DOMAIN_MODEL_LOWER}}` | Primary model lowercase | "patient" |
| `{{DOMAIN_MODEL_PLURAL}}` | Primary model plural | "patients" |
| `{{DOMAIN_MODELS}}` | All model names | "Patient, Appointment" |
| `{{INDUSTRY}}` | Prospect industry | "Healthcare" |

## File Renames

| Original | Example After |
|---|---|
| `src/models/item.py` | `src/models/patient.py` |
| `src/models/widget.py` | `src/models/appointment.py` |
| `src/routes/item_routes.py` | `src/routes/patient_routes.py` |
| `src/routes/widget_routes.py` | `src/routes/appointment_routes.py` |
| `src/services/item_service.py` | `src/services/patient_service.py` |

## Class Renames

`Item` -> `Patient`, `Widget` -> `Appointment`, etc. All imports updated automatically.
