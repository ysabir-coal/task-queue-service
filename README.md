# Task Queue Service

A lightweight task queue service built with FastAPI and Redis. Supports task submission, status polling, retry logic, and webhook notifications on completion.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest tests/ -v
```

## Architecture

- `app/main.py` — FastAPI application with REST endpoints
- `app/queue.py` — Task queue backed by Redis
- `app/worker.py` — Background worker processing tasks
- `app/models.py` — Pydantic models for request/response
- `app/notifications.py` — Webhook notification sender
- `app/config.py` — Configuration management
