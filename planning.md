# Admission AI Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working prototype of the admission AI agent described in the spec — an agent that talks to parents about admissions, tracks each applicant through a state machine, remembers case/user context, uses tools (mocked integrations) to send reminders and check status, and escalates anything risky or uncertain to a human (Divya ma'am / admission staff) for approval.

**Architecture:** A Python/FastAPI backend with a SQLite database (via SQLAlchemy) holding parents, students/applications, conversations, documents, reminders, and approval requests. A deterministic state machine (Layer 3 of the spec) enforces valid application-state transitions outside the LLM. The agent's reasoning is handled by the Claude API using tool-calling: the model decides which mocked tool to call (WhatsApp reminder, CRM status lookup, document parser, calendar booking, group-add, human-approval request); the business rules (risk gating, confidentiality checks, extension handling) live in the tool code, not in the prompt, so they're testable. A minimal server-rendered web UI lets a human simulate a parent chat and review/approve/reject pending actions.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, SQLite, `anthropic` Python SDK (Claude API) for agent reasoning, Jinja2 for the two HTML views, pytest + FastAPI TestClient for tests.

**Spec:** `spec document.docx.pdf` (project root — the "Persistence AI Agent — 10 Layer Design Workbook")

**Scope decisions (not in the spec, made to keep this a working prototype):**
- No real integrations exist (WhatsApp Business API, School CRM/SIS, Calendar API, Document Parser API) — all five are mocked/stubbed, each clearly logging what it would do in production.
- Layer 5's "vector database" is scoped down to a simple keyword-searchable JSON knowledge base — no embedding/vector service is wired in.
- Of the "10 test cases" mentioned in spec 10.5, only the 5 cases actually spelled out in the spec's evaluation table (10.7) are implemented as automated tests. Expanding to a full 10-case suite is future work.
- Layer 4's "across all customers/cases" memory (seat-filling trends, peak admission months, common roadblocks) is not implemented — it needs volume this prototype won't have. Session, case, and user-level memory (spec 4.4's other three tiers) are implemented.

## Global Constraints

- The agent must never approve/reject an admission, change school fees, grant exceptions, or disclose confidential information itself (spec 7.3) — these are human-only decisions.
- Any final decision output (admission confirmation, scholarship/fee concession, seat allotment) requires explicit human approval before it takes effect (spec 6.4).
- The agent must never store raw credit card data, bank account details, or unmasked government ID numbers (spec 4.5).
- When uncertain, the agent follows this order: search the knowledge base → try another tool/database → ask the parent for clarification → ask a human expert/staff → stop if unverifiable (spec 7.4).
- If a coordinator has granted a parent an extension on a document/fee deadline, the agent must not send an overdue/penalty-toned reminder that contradicts it (spec 4.3).
- Primary evaluation metric is accuracy of the agent's answers against the manual-process baseline (spec 10.1–10.4).

## Review Focus

- Parent asks about a student's status without their identity matching the record on file → agent must request verification, not return case data (spec 10.7 "Student status" case).
- A query falls outside the knowledge base / agent's authority → agent must escalate rather than guess (spec 7.4, 10.6).
- Parent (or agent) attempts a high-risk action (admission decision, fee exception, seat allocation) → system must create an approval request and never execute the action directly (spec 6.3–6.4).
- A student has an active, staff-granted extension → an overdue/penalty reminder for that student must be blocked rather than sent (spec 4.3).
- An invalid state transition is attempted (e.g., jumping from a terminal state back to an early one with no matching event) → the state machine must reject it, not silently apply it (spec Layer 3 table).

---

### Task 1: Project scaffolding & data models

**Files:**
- Create: `requirements.txt`
- Create: `admission_agent/__init__.py`
- Create: `admission_agent/db.py`
- Create: `admission_agent/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `admission_agent/db.py`: `engine`, `SessionLocal` (sessionmaker), `Base` (declarative base), `get_db()` — a generator yielding a `Session` and closing it after use.
  - `admission_agent/models.py` (SQLAlchemy ORM classes, all with `id: int` primary key and `created_at: datetime` unless noted):
    - `Parent(name: str, phone: str [unique], email: str | None, preferred_channel: str = "whatsapp")`
    - `Student(parent_id: FK Parent.id, name: str, dob: date, grade_applied: str, state: str = "waiting_for_student_details", pre_error_state: str | None, extension_granted_until: date | None, extension_note: str | None, added_to_group: bool = False, updated_at: datetime)`
    - `ConversationMessage(student_id: FK Student.id, role: str, content: str)`
    - `Document(student_id: FK Student.id, doc_type: str, status: str = "pending", raw_text: str | None, parsed_data: str | None)`
    - `Reminder(student_id: FK Student.id, message: str, reminder_type: str, sent_at: datetime | None, blocked: bool = False, block_reason: str | None)`
    - `ApprovalRequest(student_id: FK Student.id, action_type: str, payload: str, status: str = "pending", reason: str, resolved_at: datetime | None, resolver_note: str | None)`
    - `CalendarBooking(student_id: FK Student.id, slot_datetime: datetime)`

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
anthropic
jinja2
pytest
httpx
python-dotenv
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_models.py
def test_create_parent_and_student_round_trip(db_session):
    parent = Parent(name="Dr. Ram", phone="9990001111")
    db_session.add(parent)
    db_session.commit()

    student = Student(parent_id=parent.id, name="Suzanna", dob=date(2015, 4, 1), grade_applied="3")
    db_session.add(student)
    db_session.commit()

    fetched = db_session.query(Student).filter_by(name="Suzanna").one()
    assert fetched.state == "waiting_for_student_details"
    assert fetched.parent_id == parent.id
```

Add a `db_session` pytest fixture in `tests/conftest.py` that creates an in-memory SQLite engine (`sqlite:///:memory:`), runs `Base.metadata.create_all`, yields a session, and closes it afterward.

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` (models don't exist yet)

- [ ] **Step 4: Implement `admission_agent/db.py` and `admission_agent/models.py`**

Use `sqlalchemy.orm.DeclarativeBase` for `Base`, `create_engine("sqlite:///admission_agent.db")` for the real app engine. Each model as described in Interfaces above; `created_at`/`updated_at` default to `datetime.utcnow`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt admission_agent/__init__.py admission_agent/db.py admission_agent/models.py tests/test_models.py tests/conftest.py
git commit -m "feat: add project scaffolding and data models"
```

---

### Task 2: Application state machine

**Files:**
- Create: `admission_agent/state_machine.py`
- Test: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: nothing from Task 1 (operates on plain state strings/enum values, not ORM objects).
- Produces:
  - `ApplicationState(str, Enum)` with members (values are the lowercase/snake_case form used in `Student.state`): `WAITING_FOR_STUDENT_DETAILS`, `MISSING_STUDENT_DETAILS`, `INVALID_STUDENT_DETAILS`, `WAITING_TO_UPLOAD_DOCUMENTS`, `MISSING_DOCUMENTS`, `WAITING_FOR_VERIFICATION`, `INVALID_DOCUMENTS`, `MANUAL_REVIEW_REQUIRED`, `REVIEWING_ADMISSION_INFORMATION`, `WAITING_FOR_ADMISSION_DECISION`, `ADMISSION_APPROVED`, `ADMISSION_REJECTED`, `STUDENT_WAITLISTED`, `COMPLETING_ENROLLMENT`, `ADMISSION_OFFER_DECLINED`, `ENROLLMENT_COMPLETED`, `PAYMENT_FAILED`, `APPLICATION_WITHDRAWN`, `APPLICATION_DEADLINE_EXPIRED`, `AI_SYSTEM_ERROR`.
  - `TERMINAL_STATES: set[ApplicationState]` = `{ADMISSION_REJECTED, ADMISSION_OFFER_DECLINED, ENROLLMENT_COMPLETED, APPLICATION_WITHDRAWN, APPLICATION_DEADLINE_EXPIRED}`
  - `class InvalidTransitionError(Exception)` — raised with `(current_state, event)`.
  - `transition(current_state: ApplicationState, event: str, previous_state: ApplicationState | None = None) -> ApplicationState` — looks up `(current_state, event)` in the per-state table below; if not found, checks the global events (`withdraw_application`, `deadline_expired`, `system_error` — valid from any non-terminal state); `system_recovers` is only valid when `current_state == AI_SYSTEM_ERROR` and returns `previous_state` (raises `InvalidTransitionError` if `previous_state` is `None`). Raises `InvalidTransitionError` for any other unmatched `(state, event)` pair, including any event issued from a terminal state.

Per-state transition table (exact, from spec Layer 3 table 3.3):

```python
TRANSITIONS = {
    (WAITING_FOR_STUDENT_DETAILS, "submit_complete_details"): WAITING_TO_UPLOAD_DOCUMENTS,
    (WAITING_FOR_STUDENT_DETAILS, "submit_incomplete_details"): MISSING_STUDENT_DETAILS,
    (WAITING_FOR_STUDENT_DETAILS, "submit_invalid_details"): INVALID_STUDENT_DETAILS,
    (MISSING_STUDENT_DETAILS, "provide_missing_details"): WAITING_TO_UPLOAD_DOCUMENTS,
    (INVALID_STUDENT_DETAILS, "correct_invalid_details"): WAITING_TO_UPLOAD_DOCUMENTS,
    (WAITING_TO_UPLOAD_DOCUMENTS, "upload_all_documents"): WAITING_FOR_VERIFICATION,
    (WAITING_TO_UPLOAD_DOCUMENTS, "documents_missing"): MISSING_DOCUMENTS,
    (MISSING_DOCUMENTS, "upload_missing_documents"): WAITING_FOR_VERIFICATION,
    (WAITING_FOR_VERIFICATION, "documents_valid"): REVIEWING_ADMISSION_INFORMATION,
    (WAITING_FOR_VERIFICATION, "documents_invalid"): INVALID_DOCUMENTS,
    (INVALID_DOCUMENTS, "upload_corrected_documents"): WAITING_FOR_VERIFICATION,
    (WAITING_FOR_VERIFICATION, "documents_mismatched"): MANUAL_REVIEW_REQUIRED,
    (MANUAL_REVIEW_REQUIRED, "officer_resolves_discrepancy"): REVIEWING_ADMISSION_INFORMATION,
    (REVIEWING_ADMISSION_INFORMATION, "meets_requirements"): WAITING_FOR_ADMISSION_DECISION,
    (WAITING_FOR_ADMISSION_DECISION, "officer_approves"): ADMISSION_APPROVED,
    (WAITING_FOR_ADMISSION_DECISION, "officer_rejects"): ADMISSION_REJECTED,
    (WAITING_FOR_ADMISSION_DECISION, "qualifies_for_waitlist"): STUDENT_WAITLISTED,
    (STUDENT_WAITLISTED, "seat_available_selected"): ADMISSION_APPROVED,
    (ADMISSION_APPROVED, "accepts_offer"): COMPLETING_ENROLLMENT,
    (ADMISSION_APPROVED, "declines_offer"): ADMISSION_OFFER_DECLINED,
    (COMPLETING_ENROLLMENT, "fees_paid"): ENROLLMENT_COMPLETED,
    (COMPLETING_ENROLLMENT, "payment_fails"): PAYMENT_FAILED,
    (PAYMENT_FAILED, "retry_payment_succeeds"): ENROLLMENT_COMPLETED,
}
GLOBAL_EVENTS = {"withdraw_application": APPLICATION_WITHDRAWN, "deadline_expired": APPLICATION_DEADLINE_EXPIRED, "system_error": AI_SYSTEM_ERROR}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state_machine.py
def test_valid_transition_moves_state():
    assert transition(ApplicationState.WAITING_FOR_STUDENT_DETAILS, "submit_complete_details") == ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS

def test_global_event_withdraw_from_any_nonterminal_state():
    assert transition(ApplicationState.WAITING_FOR_VERIFICATION, "withdraw_application") == ApplicationState.APPLICATION_WITHDRAWN

def test_system_error_then_recovery_returns_previous_state():
    errored = transition(ApplicationState.MANUAL_REVIEW_REQUIRED, "system_error")
    assert errored == ApplicationState.AI_SYSTEM_ERROR
    recovered = transition(errored, "system_recovers", previous_state=ApplicationState.MANUAL_REVIEW_REQUIRED)
    assert recovered == ApplicationState.MANUAL_REVIEW_REQUIRED

def test_invalid_transition_from_terminal_state_raises():
    with pytest.raises(InvalidTransitionError):
        transition(ApplicationState.ENROLLMENT_COMPLETED, "submit_complete_details")

def test_unmatched_event_raises():
    with pytest.raises(InvalidTransitionError):
        transition(ApplicationState.WAITING_FOR_STUDENT_DETAILS, "fees_paid")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state_machine.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implement `admission_agent/state_machine.py`** with the exact enum, tables, and `transition()` behavior described above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state_machine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/state_machine.py tests/test_state_machine.py
git commit -m "feat: add application state machine"
```

---

### Task 3: Knowledge base

**Files:**
- Create: `admission_agent/knowledge/fees.json`
- Create: `admission_agent/knowledge/eligibility.json`
- Create: `admission_agent/knowledge/faq.json`
- Create: `admission_agent/knowledge_base.py`
- Test: `tests/test_knowledge_base.py`

**Interfaces:**
- Produces:
  - Each JSON file is a list of `{"id": str, "category": "fees"|"eligibility"|"faq", "topic": str, "content": str}` objects. Seed with plausible data consistent with the spec's own example (admission fee ₹25,000): a grade-wise fee table (registration fee, admission fee, term fees per grade), an age/grade eligibility table, and FAQ entries covering required certificates, the school WhatsApp group, and payment deadlines.
  - `load_knowledge_base() -> list[dict]` — reads and concatenates all three JSON files.
  - `search_knowledge_base(query: str, kb: list[dict]) -> list[dict]` — case-insensitive keyword overlap between `query` and each entry's `topic` + `content`; returns the top 3 entries by match count (empty list if nothing scores above 0).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knowledge_base.py
def test_search_finds_relevant_fee_entry():
    kb = load_knowledge_base()
    results = search_knowledge_base("admission fee for grade 3", kb)
    assert any("fee" in r["category"] for r in results)

def test_search_returns_empty_for_unrelated_query():
    kb = load_knowledge_base()
    assert search_knowledge_base("xyzxyz nonsense query", kb) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_knowledge_base.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write the three JSON seed files and implement `admission_agent/knowledge_base.py`** with `load_knowledge_base()` and `search_knowledge_base()` as specified.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_knowledge_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/knowledge admission_agent/knowledge_base.py tests/test_knowledge_base.py
git commit -m "feat: add keyword-searchable knowledge base"
```

---

### Task 4: Human-in-the-loop approval queue

**Files:**
- Create: `admission_agent/approvals.py`
- Test: `tests/test_approvals.py`

**Interfaces:**
- Consumes: `Student`, `ApprovalRequest` from `admission_agent/models.py` (Task 1); `ApplicationState`, `transition` from `admission_agent/state_machine.py` (Task 2); a SQLAlchemy `Session`.
- Produces:
  - `create_approval_request(db: Session, student_id: int, action_type: str, payload: dict, reason: str) -> ApprovalRequest` — serializes `payload` to JSON in the `payload` column, `status="pending"`.
  - `list_pending_approvals(db: Session) -> list[ApprovalRequest]`
  - `resolve_approval(db: Session, approval_id: int, decision: str, resolver_note: str | None = None) -> ApprovalRequest` — `decision` is `"approved"` or `"rejected"` (raise `ValueError` otherwise). On `"approved"`, applies the action: for `action_type == "admission_decision"`, calls `transition()` with the event in `payload["event"]` and writes the resulting state to `Student.state`; for `action_type == "fee_exception"`, writes `payload["note"]` into `Student.extension_note` and `payload["until"]` into `Student.extension_granted_until`. On `"rejected"`, only updates the `ApprovalRequest` row. Sets `resolved_at` and `resolver_note` in both cases.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_approvals.py
def test_create_and_list_pending_approval(db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "parent asked to approve")
    assert req.status == "pending"
    assert req in list_pending_approvals(db_session)

def test_approving_admission_decision_transitions_state(db_session, sample_student):
    sample_student.state = ApplicationState.WAITING_FOR_ADMISSION_DECISION.value
    db_session.commit()
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    resolve_approval(db_session, req.id, "approved", resolver_note="looks good")
    db_session.refresh(sample_student)
    assert sample_student.state == ApplicationState.ADMISSION_APPROVED.value

def test_rejecting_approval_does_not_change_student_state(db_session, sample_student):
    original_state = sample_student.state
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    resolve_approval(db_session, req.id, "rejected")
    db_session.refresh(sample_student)
    assert sample_student.state == original_state
```

Add a `sample_student` fixture in `tests/conftest.py` that creates a `Parent` + `Student` and returns the student.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_approvals.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implement `admission_agent/approvals.py`** as specified in Interfaces.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_approvals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/approvals.py tests/test_approvals.py tests/conftest.py
git commit -m "feat: add human-in-the-loop approval queue"
```

---

### Task 5: Mocked tools

**Files:**
- Create: `admission_agent/tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Student`, `Reminder`, `Document`, `CalendarBooking` from Task 1; `search_knowledge_base`, `load_knowledge_base` from Task 3; `create_approval_request` from Task 4.
- Produces:
  - `search_knowledge_base_tool(db: Session, query: str) -> list[dict]` — thin wrapper calling Task 3's functions.
  - `query_applicant_status(db: Session, student_id: int, parent_phone: str) -> dict` — loads the student and its parent; if `parent.phone != parent_phone`, returns `{"status": "verification_failed"}` without touching case data; otherwise returns `{"status": student.state, "name": student.name, "grade_applied": student.grade_applied}`.
  - `send_whatsapp_reminder(db: Session, student_id: int, message: str, reminder_type: str) -> dict` — `reminder_type` is one of `"generic"`, `"document_overdue"`, `"fee_overdue"`. If `reminder_type` is one of the `*_overdue` types and the student has `extension_granted_until >= date.today()`, creates a `Reminder` row with `blocked=True, block_reason="active_extension"` and returns `{"sent": False, "reason": "active_extension"}` instead of sending. Otherwise creates `Reminder(sent_at=utcnow())` and returns `{"sent": True}`.
  - `parse_uploaded_document(db: Session, student_id: int, doc_type: str, raw_text: str) -> dict` — regex-replaces any run of 10+ digits in `raw_text` with a masked form (`"XXXXXX" + last 4 digits`) before storing it in `Document.parsed_data`; stores `Document(status="valid")`; returns the masked dict `{"doc_type": doc_type, "masked_text": ...}`.
  - `book_interview_slot(db: Session, student_id: int, slot_datetime: datetime) -> dict` — creates a `CalendarBooking` row; returns `{"booked": True, "slot": slot_datetime.isoformat()}`.
  - `add_parent_to_whatsapp_group(db: Session, student_id: int) -> dict` — sets `Student.added_to_group = True`; returns `{"added": True}`.
  - `request_human_approval(db: Session, student_id: int, action_type: str, payload: dict, reason: str) -> dict` — calls Task 4's `create_approval_request`; returns `{"approval_id": req.id, "status": "pending"}`. This is the **only** path by which `action_type in {"admission_decision", "fee_exception"}` can ever affect the student record — tools never mutate `Student.state` for those action types directly.
  - `TOOL_SCHEMAS: list[dict]` — one Claude tool-use JSON schema per function above (name, description, input_schema), named: `search_knowledge_base`, `query_applicant_status`, `send_whatsapp_reminder`, `parse_uploaded_document`, `book_interview_slot`, `add_parent_to_whatsapp_group`, `request_human_approval`.
  - `TOOL_DISPATCH: dict[str, Callable]` — maps each schema name above to its function, for the agent's tool-execution loop (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tools.py
def test_query_applicant_status_requires_matching_phone(db_session, sample_student):
    result = query_applicant_status(db_session, sample_student.id, parent_phone="0000000000")
    assert result == {"status": "verification_failed"}

def test_query_applicant_status_returns_case_data_when_verified(db_session, sample_student):
    result = query_applicant_status(db_session, sample_student.id, parent_phone=sample_student.parent.phone)
    assert result["status"] == sample_student.state

def test_overdue_reminder_blocked_when_extension_active(db_session, sample_student):
    sample_student.extension_granted_until = date.today() + timedelta(days=5)
    db_session.commit()
    result = send_whatsapp_reminder(db_session, sample_student.id, "please submit", "document_overdue")
    assert result == {"sent": False, "reason": "active_extension"}

def test_generic_reminder_sent_even_with_active_extension(db_session, sample_student):
    sample_student.extension_granted_until = date.today() + timedelta(days=5)
    db_session.commit()
    result = send_whatsapp_reminder(db_session, sample_student.id, "hello", "generic")
    assert result == {"sent": True}

def test_parse_uploaded_document_masks_long_digit_sequences(db_session, sample_student):
    result = parse_uploaded_document(db_session, sample_student.id, "birth_certificate", "ID 123456789012 issued 2015")
    assert "123456789012" not in result["masked_text"]
    assert result["masked_text"].endswith("9012") is False or "XXXXXX" in result["masked_text"]

def test_request_human_approval_never_mutates_student_state(db_session, sample_student):
    original_state = sample_student.state
    request_human_approval(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "parent requested")
    db_session.refresh(sample_student)
    assert sample_student.state == original_state
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implement `admission_agent/tools.py`** as specified in Interfaces.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/tools.py tests/test_tools.py
git commit -m "feat: add mocked integration tools with risk gating"
```

---

### Task 6: Agent orchestrator (Claude tool-calling loop)

**Files:**
- Create: `admission_agent/agent.py`
- Create: `tests/support/fake_anthropic.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `TOOL_SCHEMAS`, `TOOL_DISPATCH` from Task 5; `ConversationMessage` from Task 1.
- Produces:
  - `SYSTEM_PROMPT: str` — built from the spec's Layer 7.5 job description verbatim ("You are an AI: Admission Assistant...You cannot: Approve or reject admissions or disclose confidential information...") plus the Layer 7.4 uncertainty-handling order, stated as instructions.
  - `class FakeAnthropicClient` (in `tests/support/fake_anthropic.py`) — constructed with a list of scripted responses (each either a final text response or a tool-use request); `.messages.create(**kwargs)` pops and returns the next scripted response, recording `kwargs` on `self.calls` for assertions. Reused by Task 9.
  - `run_agent_turn(db: Session, student_id: int, parent_message: str, client=None, max_tool_iterations: int = 6) -> str` — `client` defaults to a real `anthropic.Anthropic()` if `None`. Appends `parent_message` as a `ConversationMessage(role="parent")`. Builds the message list from all prior `ConversationMessage` rows for that student (session memory) plus a leading context block with the student's case fields (case memory: name, grade, state, parent contact/preferred channel — user memory). Calls `client.messages.create(model=..., system=SYSTEM_PROMPT, messages=..., tools=TOOL_SCHEMAS)`, and while the response's `stop_reason == "tool_use"`, executes each tool-use block via `TOOL_DISPATCH`, appends the tool results, and calls again — up to `max_tool_iterations`; if exceeded, returns a fixed "I need to check with our admission staff and will get back to you" fallback (spec 7.4 step 5: stop). Stores the final text reply as `ConversationMessage(role="agent")` and returns it.

- [ ] **Step 1: Write `tests/support/fake_anthropic.py`** implementing `FakeAnthropicClient` as specified.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_agent.py
def test_run_agent_turn_returns_final_text_with_no_tool_use(db_session, sample_student):
    client = FakeAnthropicClient([text_response("Our office hours are 9-5.")])
    reply = run_agent_turn(db_session, sample_student.id, "What are your office hours?", client=client)
    assert reply == "Our office hours are 9-5."

def test_run_agent_turn_executes_tool_then_returns_text(db_session, sample_student):
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "admission fee"}),
        text_response("The admission fee is 25,000."),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "What's the admission fee?", client=client)
    assert reply == "The admission fee is 25,000."

def test_run_agent_turn_stops_after_max_iterations(db_session, sample_student):
    client = FakeAnthropicClient([tool_use_response("search_knowledge_base", {"query": "x"})] * 10)
    reply = run_agent_turn(db_session, sample_student.id, "confusing question", client=client, max_tool_iterations=2)
    assert "admission staff" in reply.lower()

def test_run_agent_turn_persists_conversation_messages(db_session, sample_student):
    client = FakeAnthropicClient([text_response("ok")])
    run_agent_turn(db_session, sample_student.id, "hello", client=client)
    messages = db_session.query(ConversationMessage).filter_by(student_id=sample_student.id).all()
    assert [m.role for m in messages] == ["parent", "agent"]
```

`text_response(text)` and `tool_use_response(name, input)` are small helper constructors in `tests/support/fake_anthropic.py` that build objects shaped like the Anthropic SDK's response (with `.stop_reason`, `.content` blocks carrying `.type`, `.text` / `.name`+`.input`+`.id`).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 4: Implement `admission_agent/agent.py`** as specified in Interfaces.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add admission_agent/agent.py tests/support/fake_anthropic.py tests/test_agent.py
git commit -m "feat: add Claude tool-calling agent orchestrator"
```

---

### Task 7: FastAPI endpoints

**Files:**
- Create: `admission_agent/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `run_agent_turn` (Task 6), `list_pending_approvals`/`resolve_approval` (Task 4), `get_db` (Task 1), `Student` (Task 1).
- Produces:
  - `app: FastAPI`
  - `POST /chat` — body `{"student_id": int, "message": str}` → `{"reply": str}` (calls `run_agent_turn` with the real Anthropic client).
  - `GET /admin/approvals` → `[{"id", "student_id", "action_type", "payload", "reason", "status"}, ...]` for pending approvals.
  - `POST /admin/approvals/{approval_id}/decide` — body `{"decision": "approved"|"rejected", "resolver_note": str | None}` → the resolved approval as JSON.
  - `GET /admin/cases` → `[{"id", "name", "grade_applied", "state"}, ...]` for all students.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api.py (uses FastAPI TestClient with a dependency override swapping get_db for the in-memory test session, and monkeypatches run_agent_turn to avoid real API calls)
def test_chat_endpoint_returns_reply(client, sample_student, monkeypatch):
    monkeypatch.setattr("admission_agent.api.run_agent_turn", lambda db, student_id, message, **kw: "mocked reply")
    response = client.post("/chat", json={"student_id": sample_student.id, "message": "hi"})
    assert response.status_code == 200
    assert response.json() == {"reply": "mocked reply"}

def test_admin_approvals_lists_pending(client, db_session, sample_student):
    create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.get("/admin/approvals")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_admin_decide_approval_resolves_it(client, db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

def test_admin_cases_lists_students(client, sample_student):
    response = client.get("/admin/cases")
    assert response.status_code == 200
    assert any(c["id"] == sample_student.id for c in response.json())
```

Add a `client` fixture in `tests/conftest.py` building `TestClient(app)` with `app.dependency_overrides[get_db]` pointed at the test session.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implement `admission_agent/api.py`** as specified in Interfaces.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/api.py tests/test_api.py tests/conftest.py
git commit -m "feat: add chat and admin REST endpoints"
```

---

### Task 8: Minimal web UI

**Files:**
- Create: `admission_agent/templates/chat.html`
- Create: `admission_agent/templates/admin.html`
- Modify: `admission_agent/api.py` (add `GET /` and `GET /admin` routes)
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `app` from Task 7.
- Produces:
  - `GET /` — renders `chat.html`: a text input + send button posting to `/chat` via `fetch`, displaying the running conversation.
  - `GET /admin` — renders `admin.html`: a table of pending approvals (from `/admin/approvals`) with Approve/Reject buttons posting to `/admin/approvals/{id}/decide`, and a table of cases (from `/admin/cases`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ui.py
def test_root_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Send" in response.content

def test_admin_page_loads(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Approve" in response.content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui.py -v`
Expected: FAIL (404, routes don't exist)

- [ ] **Step 3: Implement the two templates and wire `Jinja2Templates` + the two routes into `admission_agent/api.py`.** Keep both pages to plain HTML + a `<script>` block using `fetch`; no build step, no JS framework.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add admission_agent/templates admission_agent/api.py tests/test_ui.py
git commit -m "feat: add minimal parent chat and admin review UI"
```

---

### Task 9: Evaluation harness

**Files:**
- Create: `tests/eval/test_evaluation_cases.py`
- Create: `docs/evaluation_results.md`

**Interfaces:**
- Consumes: `run_agent_turn` (Task 6), `FakeAnthropicClient`/`text_response`/`tool_use_response` (Task 6), `query_applicant_status` (Task 5).
- Produces: five automated tests, one per row of spec table 10.7, each scripting the `FakeAnthropicClient` to behave the way a correct agent should and asserting the expected behavior:
  1. Fee enquiry → scripted tool-use of `search_knowledge_base` then a text reply containing the fee figure from the seeded KB.
  2. Age eligibility → scripted tool-use of `search_knowledge_base` then a text reply containing "eligible" or "not eligible".
  3. Admission deadline → scripted reply containing the exact deadline string from the seeded KB (regression guard for the spec's recorded "wrong date" failure).
  4. Student status (confidentiality) → calls `query_applicant_status` directly with a mismatched phone and asserts `{"status": "verification_failed"}`, proving the agent's tool layer can't leak data regardless of what the model says.
  5. Uncertain query → scripted agent reply contains `request_human_approval` or escalation language, asserted via the fake client's recorded tool-use call name.

- [ ] **Step 1: Write the five failing tests** in `tests/eval/test_evaluation_cases.py`, one `test_case_<n>_<name>` function per case above.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/eval/test_evaluation_cases.py -v`
Expected: FAIL (behavior not yet asserted against real seeded data, or import errors)

- [ ] **Step 3: Adjust the seeded KB content (Task 3 files) if needed so the fee/deadline/eligibility cases have a concrete, assertable value, then make the tests pass.**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/eval/test_evaluation_cases.py -v`
Expected: PASS

- [ ] **Step 5: Write `docs/evaluation_results.md`** summarizing the 5 cases, expected vs. actual, matching the format of spec table 10.7, and noting the scope decision that this covers the 5 documented cases rather than the full 10 mentioned in 10.5.

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/eval docs/evaluation_results.md
git commit -m "test: add evaluation harness for spec's 5 documented cases"
```
