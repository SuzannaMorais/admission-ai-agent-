# Progress

**Last updated:** 2026-10-29

## Completed

- [x] **T1** — Project scaffolding & data models. Commit `1171c2a`. Tests: `tests/test_models.py` — 1/1 passed.
- [x] **T2** — Application state machine. Commit `c9894c6`. Tests: `tests/test_state_machine.py` — 5/5 passed.
- [x] **T3** — Knowledge base. Commit `f11b8d4`. Tests: `tests/test_knowledge_base.py` — 2/2 passed.
- [x] **T4** — Human-in-the-loop approval queue. Commit `65c62ad`. Tests: `tests/test_approvals.py` — 3/3 passed.
- [x] **T5** — Mocked tools. Commit `dfc10b1`. Tests: `tests/test_tools.py` — 6/6 passed.
- [x] **T6** — Agent orchestrator (Claude tool-calling loop). Commit `cb48a3e`. Tests: `tests/test_agent.py` — 4/4 passed.
- [x] **T7** — FastAPI endpoints. Commit `7e96ebb`. Tests: `tests/test_api.py` — 4/4 passed.
- [x] **T8** — Minimal web UI. Commit `a5094e1`. Tests: `tests/test_ui.py` — 2/2 passed.
- [x] **T9** — Evaluation harness. Commit `3a1a48d`. Tests: `tests/eval/test_evaluation_cases.py` — 5/5 passed.
- [x] **Full suite, end of Phase 1:** 32/32 passed.
- [x] **Documentation** — `implementation/` folder (7 files) created. Commit `e89afcf`.
- [x] **T10 — Final whole-branch code review.** Dispatched to an independent reviewer model against commits `962333c..3a1a48d`. Verdict: **not ready to merge** — 5 Critical, 13 Important, ~13 Minor findings. Full findings recorded in the build ledger (`../.superpowers/sdd/planning/progress.md`).
- [x] **T10a — Fix pass.** All 5 Critical + 13 Important findings fixed, each with a failing test written first, then verified green. 13 Minor findings deferred (not fixed — listed below), per the project's fix-pass rule that minors don't block a merge. Commits `140f7af`, `67556c6`, `a9140d8`, `8f3a722`, `bdc32e7`.
  - **C1** — `/chat` was missing `max_tokens` on every real Claude API call, so it could never have worked; the test double was also hardened to require it so this can't regress silently.
  - **C2** — nothing created the database schema outside the test fixture, so the app couldn't start; `init_db()` now runs at import time. Verified by actually starting the real app (not just the test-overridden one) and hitting `/`, `/admin`, `/admin/cases`, `/admin/approvals`.
  - **C3** — document parsing masked the *returned* text but stored the original unmasked ID in the adjacent `raw_text` column; both columns now store the masked form.
  - **C4** — the agent handed case data (state, parent phone) to the model unconditionally with no caller verification; `run_agent_turn` now requires a `parent_phone` and only includes case data in context when it matches the parent on file.
  - **C5** — `/admin/approvals`, `/admin/cases`, and the decide endpoint had no authentication; they're now gated behind a bearer-token check (`ADMIN_TOKEN`). The bare `/admin` page shell is intentionally left ungated — see the ruling below.
  - **I1** — `book_interview_slot` couldn't accept the ISO string its own tool schema advertised, and the failure poisoned the DB session for the rest of the turn; it now parses ISO strings.
  - **I2** — tool execution had no error handling; unknown tool names or tool exceptions now become a recoverable `tool_result` with `is_error: true` instead of an unhandled crash.
  - **I3** — `resolve_approval` could be called twice on the same request; it now raises `ApprovalAlreadyResolvedError` if the request isn't still `pending`.
  - **I4** — approval-decide failures were silent 500s; they're now mapped to 404/409/400, and the admin UI now checks `response.ok` and alerts on failure.
  - **I5** — approving an unrecognized `action_type` silently "succeeded" with no effect; both `request_human_approval` and `resolve_approval` now reject unknown action types.
  - **I6** — the extension-aware reminder block was keyed on the model-supplied `reminder_type` label, not the message content; it now also screens message text for overdue/penalty wording regardless of label.
  - **I7** — the ID-masking regex missed space/hyphen-separated digit groups (the normal way an Aadhaar or card number is written); it now matches those too.
  - **I8** — the admin page built table rows via `innerHTML` with unescaped parent/LLM-influenced text (stored XSS risk); rows are now built with `textContent`.
  - **I9** — the admin page didn't show the approval payload a staff member was approving; it now renders it.
  - **I10** — an empty model reply could be persisted and returned to the parent as `""`; it now falls back to the staff-escalation message.
  - **I11** — the parent's message was persisted before the student ID was validated (orphan rows on a bad ID), and SQLite foreign keys weren't enforced; student validation now happens first, and FK enforcement is turned on for the real engine.
  - **I12** — one of the five evaluation cases (age eligibility) was fully decoupled from the seeded knowledge base; it now asserts against the real KB entry like the other cases.
  - **I13** — there was no test proving the *agent turn* (not just the tool) withholds case data from an unverified caller; added alongside the C4 fix.
- [x] **Final suite after fix pass: 57/57 passed.**
- [x] **GitHub access check** — confirmed `WRITE` permission on `SuzannaMorais/admission-ai-agent-`; confirmed the remote repository had no branches (empty) before this push.

## Deferred (Minor findings — not fixed, by design)

These were explicitly set aside per the project's rule that Minor findings go to a deferred list rather than the fix pass:
- `MODEL` hardcoded in `agent.py` with no env override.
- `knowledge_base.py` search has no stopword filtering (noisy ranking).
- `python-dotenv` listed in `requirements.txt` but never used.
- `query_applicant_status`'s failure case overloads the same `"status"` key a real state would use.
- `search_knowledge_base_tool` takes an unused `db` param; a redundant dispatch wrapper exists in `tools.py`.
- `_utcnow()` is duplicated identically in three files.
- `Student.updated_at` is never actually updated by any code path.
- `parse_uploaded_document` hardcodes `status="valid"` regardless of content — the `invalid_documents`/`manual_review_required` states have no real producer yet.
- `Student.pre_error_state` is never persisted outside the pure state-machine function's parameter.
- `approvals.py` raises a bare `ValueError` for an unrecognized stored state instead of the domain's `InvalidTransitionError`.
- `requirements.txt` is almost entirely unpinned.
- No `tests/__init__.py` / `tests/support/__init__.py` — relies on implicit namespace packages.
- The `client` test fixture's teardown clears *all* dependency overrides rather than restoring prior state.

## Pending (not started)

- [ ] **T11 — Full login/session system for staff.** The bearer-token check added in the fix pass is a stopgap; a real login flow is still future work.
- [ ] **T12 — One real integration spike.** Blocked on real API credentials (WhatsApp Business API or equivalent) — none exist in this environment.
- [ ] **T13 — Expand evaluation to the full 10 cases.** Blocked on the remaining 5 case definitions, which must come from the school/project owner, not be invented.
- [ ] **T14 — Live-model evaluation.** Not started; depends on `ANTHROPIC_API_KEY` being available at run time.
- [ ] The 13 deferred Minor findings above, if/when prioritized.

## Files changed in this work session

Implementation (Phase 1 + fix pass, all committed): `requirements.txt`, `admission_agent/**`, `tests/**`, `docs/evaluation_results.md`, root `README.md`.

Documentation: `implementation/README.md`, `implementation/planning.md`, `implementation/architecture.md`, `implementation/implementation-plan.md`, `implementation/testing.md`, `implementation/CLAUDE.md`, `implementation/progress.md` (this file).

## Tests executed and their results (this session)

| Command | Result |
|---|---|
| `./.venv/Scripts/python -m pytest -v` (end of Phase 1, before review) | 32 passed |
| `./.venv/Scripts/python -m pytest -v` (after full fix pass) | 57 passed |
| Manual smoke test: `TestClient` against the real (non-test-override) app and engine, hitting `/`, `/admin`, `/admin/cases`, `/admin/approvals` | all 200 |

## Important technical decisions (rulings)

Recorded in full in the build ledger at `../.superpowers/sdd/planning/progress.md`. Summary:
- The test `db_session` fixture needed `StaticPool` + `check_same_thread=False` for SQLite's in-memory DB to survive FastAPI `TestClient`'s background thread. Test-infrastructure-only; no production impact.
- One API test needed its fixture student placed in `WAITING_FOR_ADMISSION_DECISION` before approving, because the approval queue correctly enforces the real state machine rather than skipping validation.
- The evaluation harness (T9) required no production code changes on first run — it exercises already-built functionality.
- The `GET /admin` page shell is intentionally left ungated while its underlying data/action endpoints are hard-gated: the chosen auth mechanism is a Bearer header, which can't be attached to a plain browser navigation GET, so gating the inert HTML shell would make the page unreachable through normal navigation. The page prompts for the token in JS and attaches it to every real fetch call instead. Cost if wrong: the page reveals a staff UI exists at `/admin` with no data behind it; a future real login system (T11) supersedes this.
- Documentation reflects the *local* repository state (branch `implement-admission-agent`) because the target GitHub repository was empty before this push — there was nothing there to analyze or preserve.
