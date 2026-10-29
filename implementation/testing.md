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

**57 passed** — run after the post-review fix pass, command `./.venv/Scripts/python -m pytest -v`, no failures, no warnings. (32 passed at the end of Phase 1, before the independent code review added 25 more tests across the fix pass.) This was executed, not assumed. If you run it again and get a different number, trust what you just saw, not this file — update this file to match.

## Test inventory by file

| File | What it covers | Count |
|---|---|---|
| `tests/test_models.py` | ORM round-trip (Parent/Student creation, default state) | 1 |
| `tests/test_db.py` | `init_db()` creates every model's table on a fresh engine | 1 |
| `tests/test_state_machine.py` | Valid transitions, global events, error/recovery, terminal-state and unmatched-event rejection | 5 |
| `tests/test_knowledge_base.py` | Keyword search relevance and empty-result behavior | 2 |
| `tests/test_approvals.py` | Approval creation/listing, approve→state-transition, reject→no-change, idempotency, unknown action-type rejection, resolved-by recording | 6 |
| `tests/test_tools.py` | Phone-verified status lookup, extension-aware reminder blocking (by type and by content), document ID masking (contiguous and space-separated), approval-only mutation of high-risk fields, unknown action-type rejection, ISO-string interview booking | 12 |
| `tests/test_agent.py` | No-tool reply, tool-then-reply, max-iteration fallback, conversation persistence, empty-reply fallback, unknown-student rejection with no orphan writes, recovery from an unknown tool name, confidentiality withheld/granted by phone verification | 9 |
| `tests/test_api.py` | `/chat` (incl. parent-phone pass-through), `/admin/approvals` (list/decide), `/admin/cases`, admin-auth rejection, and 404/409/400 mapping for approval-decide failures | 13 |
| `tests/test_ui.py` | `/` and `/admin` render their key elements, chat page collects/sends `parent_phone`, admin page avoids unsafe `innerHTML` and renders the approval payload | 6 |
| `tests/eval/test_evaluation_cases.py` | The 5 spec-documented evaluation cases (fee, eligibility, deadline, confidentiality, escalation) | 5 |

**Total: 57.**

## What is and isn't covered

### Covered (integration-level, real code paths)
- The state machine's full transition table, including rejection of invalid transitions from terminal states.
- The approval queue actually mutating `Student.state`/`extension_*` fields, not just recording a status, including idempotency (can't resolve twice) and unknown-action-type rejection.
- The confidentiality guard both at the tool level (`query_applicant_status`) **and** at the agent-turn level (`run_agent_turn` withholds case data from the Claude context block when the caller's phone doesn't match) — this was a real gap the independent review caught (see `architecture.md`/`progress.md`).
- Admin-endpoint authentication: requests without a valid bearer token are rejected (401) from `/admin/approvals`, `/admin/cases`, and the decide endpoint.
- The FastAPI layer end-to-end (`TestClient`, real routing, real DB session via dependency override), including a manual smoke test against the *real*, non-test-overridden app and engine (see `progress.md`).
- Government-ID masking actually persists the masked form everywhere (`raw_text` and `parsed_data`), not just in the returned value, and now also catches space/hyphen-separated digit groups.

### Not covered
- **Full login/session auth:** the bearer-token check added in the fix pass is a stopgap (anyone with the shared `ADMIN_TOKEN` has full staff access, and there's no per-user audit beyond the `resolved_by` field staff type in themselves). A real login system is still future work (T11).
- **Real Claude model behavior:** every agent test (`test_agent.py`, `test_evaluation_cases.py`) scripts a `FakeAnthropicClient` to return pre-determined responses. These tests prove the surrounding system (tool dispatch, persistence, risk gating) behaves correctly *given* a correct model response — they do not prove the real model will produce that response. No test in this repository has called the real Anthropic API. The fake client was hardened during the fix pass to require `model`/`max_tokens`/`messages`, which is what caught the missing-`max_tokens` bug in the first place.
- **Real external integrations:** WhatsApp, CRM/SIS, Calendar, and Document Parser are all mocked in `tools.py`. There is no integration test against any real external API because none are wired up.
- **Load/concurrency testing:** none. SQLite + no connection pooling tuning means this has not been tested under concurrent load.
- **End-to-end browser testing of the UI:** the UI tests check page content/structure (including the absence of unsafe `innerHTML` patterns), not actual rendered/clicked behavior; no browser automation has clicked through the chat or admin flows.

## Known test-environment notes

- `tests/conftest.py`'s `db_session` fixture uses an in-memory SQLite engine with `StaticPool` and `check_same_thread=False`. This is required because FastAPI's `TestClient` can execute requests on a different thread than the one that created the fixture, and SQLite's `:memory:` database is otherwise per-connection — without this, a second thread sees "no such table" against what looks like a fresh empty database. This only affects the test fixture; the real app (Task 1) uses a file-based `sqlite:///admission_agent.db`, which doesn't have this failure mode.
- The evaluation harness (Task 9) passed on its first run without any implementation changes — it exercises already-built code (Tasks 3/5/6) end-to-end rather than driving new production code, so there was no red→green cycle for that task specifically.

## Security / regression testing performed

- Government-ID-shaped digit masking (`test_parse_uploaded_document_masks_long_digit_sequences`) — regression guard against ever storing a readable long ID number.
- Confidentiality (`test_query_applicant_status_requires_matching_phone`, and the eval-suite's case 4) — regression guard against leaking case data to an unverified requester.
- Risk-gating (`test_request_human_approval_never_mutates_student_state`) — regression guard against an admission decision or fee exception ever taking effect without going through the approval queue.

No dedicated security scanning tool (e.g. `bandit`, `pip-audit`) has been run against this codebase. **Proposed** for Phase 2.
