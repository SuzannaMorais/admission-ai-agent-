# Admission AI Agent

A prototype AI agent that manages a school's admission enquiry-to-enrolment lifecycle: answers parent questions, tracks applicants through a state machine, sends reminders, and escalates anything risky to a human for approval. Built from the design spec in `spec document.docx.pdf`.

Full documentation (architecture, plan, testing, progress) lives in [`implementation/`](implementation/README.md).

## Setup

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt                 # macOS/Linux
```

## Configuration

| Variable | Required for | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Real `/chat` traffic | Not needed to run the test suite (tests inject a fake model client). |
| `ADMIN_TOKEN` | `/admin/*` endpoints | The admin UI (`/admin`) will prompt for this value and send it as `Authorization: Bearer <token>`. Without it set, admin endpoints return 503. |

## Run

```bash
export ANTHROPIC_API_KEY=sk-...      # PowerShell: $env:ANTHROPIC_API_KEY="sk-..."
export ADMIN_TOKEN=some-secret       # PowerShell: $env:ADMIN_TOKEN="some-secret"
./.venv/Scripts/python -m uvicorn admission_agent.api:app --reload
```

The database schema is created automatically on startup (`admission_agent.db`, gitignored). There is no seed data — create a `Parent`/`Student` row yourself (e.g. via a Python shell using `admission_agent.db.SessionLocal` and `admission_agent.models`) before testing `/chat` against a real student ID.

- Parent chat: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/admin

## Test

```bash
./.venv/Scripts/python -m pytest -v
```

## What's mocked

WhatsApp, School CRM/SIS, Calendar, and Document Parser integrations are all mocked in `admission_agent/tools.py` — there are no real credentials or endpoints wired in. See [`implementation/architecture.md`](implementation/architecture.md) for details.
