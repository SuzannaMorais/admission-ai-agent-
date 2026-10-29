# Testing

## Tooling

- Test runner: `pytest` (via the project's virtual environment).
- API testing: FastAPI's `TestClient` (`starlette.testclient`), driven by `httpx`.
- No separate lint, type-check, or build tooling is configured in this repository yet — there is no `ruff`/`flake8`/`mypy` config and no `pyproject.toml`. **Proposed:** add at least a linter before Phase 2 work lands.

## How to run the suite

```bash
cd "admission ai agent"
./.venv/Scripts/python -m pytest -v
```

(On a fresh machine: create the venv and install first — `python -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt`.)

## Actual last-known result

**32 passed** — run at the end of Phase 1 (Task 9), command `./.venv/Scripts/python -m pytest -v`, no failures, no warnings. This was executed, not assumed. If you run it again and get a different number, trust what you just saw, not this file — update this file to match.

## Test inventory by file

| File | What it covers | Count |
|---|---|---|
| `tests/test_models.py` | ORM round-trip (Parent/Student creation, default state) | 1 |
| `tests/test_state_machine.py` | Valid transitions, global events, error/recovery, terminal-state and unmatched-event rejection | 5 |
| `tests/test_knowledge_base.py` | Keyword search relevance and empty-result behavior | 2 |
| `tests/test_approvals.py` | Approval creation/listing, approve→state-transition, reject→no-change | 3 |
| `tests/test_tools.py` | Phone-verified status lookup, extension-aware reminder blocking, document ID masking, approval-only mutation of high-risk fields | 6 |
| `tests/test_agent.py` | No-tool reply, tool-then-reply, max-iteration fallback, conversation persistence | 4 |
| `tests/test_api.py` | `/chat`, `/admin/approvals` (list/decide), `/admin/cases` over a real `TestClient` | 4 |
| `tests/test_ui.py` | `/` and `/admin` pages render with their key elements | 2 |
| `tests/eval/test_evaluation_cases.py` | The 5 spec-documented evaluation cases (fee, eligibility, deadline, confidentiality, escalation) | 5 |

**Total: 32.**

## What is and isn't covered

### Covered (integration-level, real code paths)
- The state machine's full transition table, including rejection of invalid transitions from terminal states.
- The approval queue actually mutating `Student.state`/`extension_*` fields, not just recording a status.
- The confidentiality guard in `query_applicant_status` — this is tested directly against the real function, not through a mocked model.
- The FastAPI layer end-to-end (`TestClient`, real routing, real DB session via dependency override).

### Not covered
- **Authentication/authorization tests:** none exist, because there is no auth to test (see `architecture.md`). This is a gap, not a pass.
- **Real Claude model behavior:** every agent test (`test_agent.py`, `test_evaluation_cases.py`) scripts a `FakeAnthropicClient` to return pre-determined responses. These tests prove the surrounding system (tool dispatch, persistence, risk gating) behaves correctly *given* a correct model response — they do not prove the real model will produce that response. No test in this repository has called the real Anthropic API.
- **Real external integrations:** WhatsApp, CRM/SIS, Calendar, and Document Parser are all mocked in `tools.py`. There is no integration test against any real external API because none are wired up.
- **Load/concurrency testing:** none. SQLite + no connection pooling tuning means this has not been tested under concurrent load.
- **End-to-end browser testing of the UI:** the UI tests only check that the pages return 200 and contain an expected string; no browser automation has clicked through the chat or admin flows.

## Known test-environment notes

- `tests/conftest.py`'s `db_session` fixture uses an in-memory SQLite engine with `StaticPool` and `check_same_thread=False`. This is required because FastAPI's `TestClient` can execute requests on a different thread than the one that created the fixture, and SQLite's `:memory:` database is otherwise per-connection — without this, a second thread sees "no such table" against what looks like a fresh empty database. This only affects the test fixture; the real app (Task 1) uses a file-based `sqlite:///admission_agent.db`, which doesn't have this failure mode.
- The evaluation harness (Task 9) passed on its first run without any implementation changes — it exercises already-built code (Tasks 3/5/6) end-to-end rather than driving new production code, so there was no red→green cycle for that task specifically.

## Security / regression testing performed

- Government-ID-shaped digit masking (`test_parse_uploaded_document_masks_long_digit_sequences`) — regression guard against ever storing a readable long ID number.
- Confidentiality (`test_query_applicant_status_requires_matching_phone`, and the eval-suite's case 4) — regression guard against leaking case data to an unverified requester.
- Risk-gating (`test_request_human_approval_never_mutates_student_state`) — regression guard against an admission decision or fee exception ever taking effect without going through the approval queue.

No dedicated security scanning tool (e.g. `bandit`, `pip-audit`) has been run against this codebase. **Proposed** for Phase 2.
