# Admission AI Agent — Implementation Overview

## Project name and purpose

**Admission AI Agent** — an AI agent that owns the admission-enquiry-to-enrolment lifecycle for a school: it talks to parents, tracks each applicant through a defined state machine, remembers case/parent context, uses tools to send reminders and check status, and escalates anything risky or uncertain to a human admission staff member for approval.

The project originates from a hand-written 10-layer design workbook (`../spec document.docx.pdf`) produced by the school's admission admin ("Divya ma'am"). This `implementation/` folder documents the working prototype built from that spec.

## Main objectives and expected outcomes

- Stop parents from being dropped after the initial enquiry by automating follow-up reminders.
- Track certificate/document submission per applicant instead of manually.
- Let the agent answer routine fee/eligibility/deadline questions, while keeping every irreversible decision (admission approval/rejection, fee exceptions, seat allocation) behind explicit human approval.
- Prove the agent's accuracy against the manual process on a small set of documented evaluation cases.

## Existing technology stack (verified in the repo)

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| ORM / DB | SQLAlchemy 2.x over SQLite |
| Agent reasoning | Anthropic Claude API (`anthropic` Python SDK), tool-calling |
| Templating | Jinja2 (server-rendered, no JS build step) |
| Tests | pytest, FastAPI `TestClient`, httpx |

Full dependency list: `../requirements.txt`.

## Current project status (as of 2026-10-29)

- All 9 tasks of the original implementation plan (`../planning.md`) are complete.
- An independent code review of the full branch found 5 Critical + 13 Important issues (the app couldn't actually start or serve a real chat request, confidential data could leak, admin approvals had no auth). All of them were fixed, each with a failing test written first — see `progress.md` for the full list. 13 Minor findings were explicitly deferred, not fixed.
- **57/57 automated tests pass.** Command: `./.venv/Scripts/python -m pytest -v` (run from the repository root).
- Admin endpoints now require a shared bearer token (`ADMIN_TOKEN`); this is a stopgap, not a real login system (see `architecture.md` → Authentication). `/chat` now requires `parent_phone` and only shows case data to the model when it matches the parent on file.
- All five external integrations (WhatsApp, School CRM/SIS, Calendar, Document Parser) are still **mocked** — there are no real credentials or endpoints wired in. See [`architecture.md`](architecture.md) for exactly what each mock does.

## Folder and file map

```
implementation/
├── README.md               — this file
├── planning.md              — problem statement, users, requirements, edge cases, scope
├── architecture.md          — technical architecture, data flow, diagrams
├── implementation-plan.md   — task-by-task build plan with status
├── testing.md               — how to run tests, what's covered, what isn't
├── CLAUDE.md                 — instructions for any AI assistant editing this repo
└── progress.md               — live tracking: done / in progress / pending / blocked
```

Everything here describes the actual code in the repository root (`admission_agent/`, `tests/`, root `planning.md`). Where something is proposed but not built, it is labelled **Proposed** — never presented as done.

## Using and maintaining this folder

- Before editing any implementation file, read [`CLAUDE.md`](CLAUDE.md) — it is the standing instruction set for how changes to this repo should be made and documented.
- After any change to `admission_agent/` or `tests/`, update the relevant doc(s) here in the same change — especially [`progress.md`](progress.md) and, if test coverage changed, [`testing.md`](testing.md).
- Do not let this folder drift from the code. If a doc and the code disagree, the code is the source of truth until the doc is corrected.
