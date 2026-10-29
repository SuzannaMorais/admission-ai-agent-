# Implementation Plan

This restates the task-by-task plan that was actually executed (full detail, exact signatures, and test code: `../planning.md` at the repository root) in the task-tracking format this folder uses, and extends it with the next, not-yet-started phase. Tasks 1–9 below are complete; everything from Task 10 onward is **Proposed** — none of it has been started.

## Phase 1 — Prototype build (complete)

### Task 1: Project scaffolding & data models
- **Objective:** Stand up the Python project and the 7 core ORM models.
- **Files:** `requirements.txt`, `admission_agent/__init__.py`, `admission_agent/db.py`, `admission_agent/models.py`, `tests/test_models.py`, `tests/conftest.py`.
- **Dependencies:** none.
- **Acceptance criteria:** a `Parent` + `Student` can be created and round-tripped through an in-memory SQLite DB; `Student.state` defaults to `"waiting_for_student_details"`.
- **Testing:** `tests/test_models.py::test_create_parent_and_student_round_trip`.
- **Status:** ✅ Done (commit `1171c2a`).

### Task 2: Application state machine
- **Objective:** Encode spec Layer 3's full transition table as a pure, DB-independent function.
- **Files:** `admission_agent/state_machine.py`, `tests/test_state_machine.py`.
- **Dependencies:** Task 1 (shares the state-string contract with `Student.state`, no code dependency).
- **Acceptance criteria:** valid transitions succeed; global events (withdraw/deadline/system-error) work from any non-terminal state; `system_recovers` returns to the stored previous state; terminal states and unmatched events raise `InvalidTransitionError`.
- **Testing:** 5 tests in `tests/test_state_machine.py`.
- **Status:** ✅ Done (commit `c9894c6`).

### Task 3: Knowledge base
- **Objective:** Seed and search fee/eligibility/FAQ data.
- **Files:** `admission_agent/knowledge/{fees,eligibility,faq}.json`, `admission_agent/knowledge_base.py`, `tests/test_knowledge_base.py`.
- **Dependencies:** none.
- **Acceptance criteria:** a relevant query returns the matching category's entries; an unrelated query returns nothing.
- **Testing:** 2 tests in `tests/test_knowledge_base.py`.
- **Status:** ✅ Done (commit `f11b8d4`).

### Task 4: Human-in-the-loop approval queue
- **Objective:** The only code path that can act on an admission decision or fee exception.
- **Files:** `admission_agent/approvals.py`, `tests/test_approvals.py`.
- **Dependencies:** Task 1 (models), Task 2 (`transition`).
- **Acceptance criteria:** creating and listing pending approvals works; approving an `admission_decision` drives a real state transition; rejecting leaves student state untouched.
- **Testing:** 3 tests in `tests/test_approvals.py`.
- **Status:** ✅ Done (commit `65c62ad`).

### Task 5: Mocked tools
- **Objective:** The 7 mocked integration tools plus their Claude tool schemas.
- **Files:** `admission_agent/tools.py`, `tests/test_tools.py`.
- **Dependencies:** Tasks 1, 3, 4.
- **Acceptance criteria:** phone-mismatched status lookups never return case data; overdue reminders are blocked when an extension is active (generic reminders are not); long digit runs in parsed documents are masked; `request_human_approval` never mutates student state directly.
- **Testing:** 6 tests in `tests/test_tools.py`.
- **Status:** ✅ Done (commit `dfc10b1`).

### Task 6: Agent orchestrator
- **Objective:** Claude tool-calling loop over the mocked tools, with session/case/user context and a bounded-iteration safety fallback.
- **Files:** `admission_agent/agent.py`, `tests/support/fake_anthropic.py`, `tests/test_agent.py`.
- **Dependencies:** Task 5 (tools), Task 1 (`ConversationMessage`).
- **Acceptance criteria:** a no-tool reply passes through; a tool-use round executes and continues; exceeding `max_tool_iterations` returns the fixed escalation fallback; both parent and agent turns are persisted.
- **Testing:** 4 tests in `tests/test_agent.py`.
- **Status:** ✅ Done (commit `cb48a3e`).

### Task 7: FastAPI endpoints
- **Objective:** `/chat` and the 3 `/admin/*` endpoints.
- **Files:** `admission_agent/api.py`, `tests/test_api.py`.
- **Dependencies:** Tasks 4, 6, 1.
- **Acceptance criteria:** chat returns the agent's reply; approvals list/decide/cases-list all work end to end through the real FastAPI `TestClient`.
- **Testing:** 4 tests in `tests/test_api.py`.
- **Status:** ✅ Done (commit `7e96ebb`). Two implementation-time rulings are recorded in the build ledger (`../.superpowers/sdd/planning/progress.md`): the test DB fixture needed `StaticPool` + `check_same_thread=False` for SQLite to survive `TestClient`'s background thread, and one test needed its fixture student placed in the correct starting state before exercising an approval.

### Task 8: Minimal web UI
- **Objective:** A parent chat page and a staff admin page, no build step.
- **Files:** `admission_agent/templates/{chat,admin}.html`, `admission_agent/api.py` (routes added).
- **Dependencies:** Task 7.
- **Acceptance criteria:** both pages load and contain their key interactive elements ("Send", "Approve").
- **Testing:** 2 tests in `tests/test_ui.py`.
- **Status:** ✅ Done (commit `a5094e1`).

### Task 9: Evaluation harness
- **Objective:** Automate the 5 cases spec Layer 10.7 documents.
- **Files:** `tests/eval/test_evaluation_cases.py`, `docs/evaluation_results.md`.
- **Dependencies:** Tasks 5, 6.
- **Acceptance criteria:** fee enquiry, age eligibility, admission deadline, confidentiality (status lookup), and escalation (uncertain query) each behave correctly when the model is scripted to behave correctly.
- **Testing:** 5 tests in `tests/eval/test_evaluation_cases.py`.
- **Status:** ✅ Done (commit `3a1a48d`).

**Full-suite result at end of Phase 1:** 32/32 tests passed. Command: `./.venv/Scripts/python -m pytest -v` (from repository root).

## Phase 2 — Review, hardening, and GitHub integration (in progress / proposed)

### Task 10: Act on final whole-branch code review
- **Objective:** A fresh-context review of commits `962333c..3a1a48d` against the plan's Review Focus section, then fix any Critical/Important findings.
- **Files:** TBD — depends entirely on what the review finds.
- **Dependencies:** Phase 1 complete.
- **Acceptance criteria:** every Critical/Important finding is either fixed with a RED→GREEN test or explicitly ruled on and recorded; full suite stays green after fixes.
- **Testing:** targeted regression test per fix, then full suite.
- **Status:** 🔄 In progress — review dispatched, result not yet landed. Do not report this task as done until `progress.md` records the actual findings and fix outcome.

### Task 11: Authentication on `/admin/*`
- **Objective:** Close the no-auth gap documented in `architecture.md`.
- **Files (expected):** `admission_agent/api.py`, a new auth module, `tests/test_api.py` additions.
- **Dependencies:** Task 10.
- **Acceptance criteria:** an unauthenticated request to any `/admin/*` route is rejected; authenticated staff can still use the dashboard.
- **Testing:** new tests for the unauthenticated-rejection case and the authenticated-success case.
- **Status:** ⬜ Not started.

### Task 12: Real integration behind one mocked tool, as a spike
- **Objective:** Replace one mock (most likely WhatsApp reminders, since that's the spec's most-cited pain point) with a real API call, behind a feature flag, so the rest of the system is proven against something live before committing to all five.
- **Dependencies:** Task 10; real API credentials from the school/WhatsApp Business account (not available at the time of writing).
- **Acceptance criteria:** a real message is sent and logged in a staging environment; mocked behavior remains the default without credentials configured.
- **Testing:** integration test gated behind an environment flag so CI without credentials still passes.
- **Status:** ⬜ Not started. Blocked on credentials.

### Task 13: Expand the evaluation harness toward the full 10 cases
- **Objective:** Spec 10.5 mentions 10 test cases; only the 5 the spec's own table documents are automated today.
- **Dependencies:** none technical; needs the remaining 5 cases defined (by the school, not invented).
- **Status:** ⬜ Not started. Blocked on case definitions from the project owner.

### Task 14: Live-model evaluation
- **Objective:** Run the 5 (or 10) evaluation cases against the real Claude API instead of a scripted fake client, to measure actual model accuracy, not just plumbing correctness.
- **Dependencies:** `ANTHROPIC_API_KEY`, Task 13 ideally.
- **Status:** ⬜ Not started.

Nothing in Phase 2 should be reported as done until the corresponding commit exists and its test command has actually been run — see `CLAUDE.md` for the standing rule on this.
