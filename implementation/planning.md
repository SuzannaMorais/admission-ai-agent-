# Project Planning

> This document is the product/requirements planning view. For the task-by-task TDD build plan that was actually executed, see `../planning.md` at the repository root. This file explains *why* and *for whom*; the root `planning.md` explains *how it was built*.

## Problem statement

The school's admission admin currently runs the enquiry-to-enrolment process by hand:

- After a parent is briefed, they say they'll check and follow up — then forget. Nothing automatically reminds them.
- Adding a parent's phone number to the relevant grade's school WhatsApp group is a manual step.
- There is no checklist tracking which required certificates each applicant has actually submitted.

Source: the hand-written spec (`../spec document.docx.pdf`, "Persistence AI Agent — 10 Layer Design Workbook"), Framing / Before Layer section.

## Project vision and objectives

Build an AI agent that owns the admission enquiry lifecycle end to end — enquiry, baseline test, registration fee, document verification, admission fee, term fees, enrolment — remembering parent/case context, using tools to send reminders and check status, and asking a human whenever a decision is risky, uncertain, or outside its authority. Success is measured by accuracy improvement over the manual process (spec Layer 10).

## Target users and their requirements

| User | Role | Requirement |
|---|---|---|
| Admission admin ("Divya ma'am") | Primary user, 75% of her time is admissions work | Needs follow-ups and reminders automated so applicants don't fall through the cracks; needs a single place to approve/reject the agent's escalations |
| Parents | Benefit from the agent, do not use it directly as an "operator" | Need accurate fee/eligibility/deadline answers and timely reminders, without their child's confidential data being exposed to the wrong person |
| School / institution | Pays for the system | Needs confidential data (student records, payment details) protected, and no irreversible decision made without a human sign-off |

## Existing features (verified in the repository) vs. proposed features

### Verified — built and tested

- Deterministic application state machine covering the full spec Layer 3 transition table, including global events (withdraw, deadline-expired, system-error/recovery) and terminal-state rejection. (`admission_agent/state_machine.py`)
- Parent/Student/Conversation/Document/Reminder/ApprovalRequest/CalendarBooking data model. (`admission_agent/models.py`)
- Keyword-searchable knowledge base seeded with grade-wise fees, age eligibility, and FAQs. (`admission_agent/knowledge_base.py`, `admission_agent/knowledge/*.json`)
- Human-in-the-loop approval queue: admission decisions and fee exceptions only take effect once a human resolves a pending `ApprovalRequest`. (`admission_agent/approvals.py`)
- Seven mocked tools: knowledge-base search, applicant status lookup (phone-verified), WhatsApp reminder (with extension-aware overdue blocking), document parsing (government-ID masking), interview booking, WhatsApp-group add, and human-approval request. (`admission_agent/tools.py`)
- Claude tool-calling agent orchestrator with session/case/user-level context and a bounded tool-iteration loop with a safe fallback. (`admission_agent/agent.py`)
- REST API (`/chat`, `/admin/approvals`, `/admin/approvals/{id}/decide`, `/admin/cases`) and a two-page server-rendered UI (parent chat, admin review). (`admission_agent/api.py`, `admission_agent/templates/`)
- Automated evaluation of the 5 cases documented in spec Layer 10.7. (`tests/eval/test_evaluation_cases.py`, `docs/evaluation_results.md`)

### Proposed — not built, explicitly out of scope for this prototype

- Real integrations with WhatsApp Business API, School CRM/SIS, Calendar API, Document Parser API. All five are currently mocked (see `architecture.md`).
- A real vector-embedding knowledge base. The current knowledge base is keyword-overlap search over seeded JSON, not an embedding/vector store.
- The full "10 test cases" mentioned in spec 10.5 — only the 5 cases the spec's own table (10.7) documents are automated.
- Cross-case/aggregate memory (seat-filling trends, peak admission months, common roadblocks) — spec Layer 4.4's fourth memory tier. Needs real usage volume this prototype doesn't have.
- **Real login/session authentication** on the admin UI — a code review caught that the admin endpoints originally had no auth at all; a stopgap shared bearer token (`ADMIN_TOKEN`) now gates them, but there's no per-user login or verified identity behind `resolved_by`. This is still a real gap for anything beyond a small trusted staff (see `architecture.md` → Authentication and `testing.md` → known gaps).

## Functional requirements

1. A parent can message the agent and get accurate answers about fees, eligibility, and deadlines, sourced from the knowledge base.
2. The agent can send reminders, but must never send an "overdue"-toned reminder to a student who has an active, staff-granted extension.
3. The agent can look up an applicant's status only after the requester's phone number matches the parent on file.
4. Any admission decision (approve/reject/waitlist) or fee exception must go through a human-approval request; the agent itself can never flip those values directly.
5. The application state machine must reject invalid transitions (e.g., a terminal state receiving a new event) rather than silently applying them.
6. Admission staff have a single view to see pending approvals and resolve them.

## Non-functional requirements

- **Security/privacy:** never store raw payment card data, bank details, or unmasked government ID numbers (spec 4.5). Document parsing masks any 10+ digit run before storage.
- **Confidentiality:** case data is never returned to a requester whose phone doesn't match the parent on file.
- **Accessibility:** **not addressed yet.** The current templates (`chat.html`, `admin.html`) are plain HTML/CSS/JS with no ARIA roles, keyboard-navigation testing, or screen-reader verification. Flagged as a known gap, not a verified property.
- **Performance:** untested at any real scale. SQLite is adequate for a single-admin prototype; it is not a production-concurrency datastore.

## User workflows and expected behaviour

1. **Parent enquiry → chat.** Parent sends a message through `/chat` (or the chat UI). The agent answers directly for routine questions, or calls a tool (knowledge-base search, status check) first.
2. **Reminder cycle.** A reminder tool call checks for an active extension before sending anything overdue-toned; if blocked, it's logged as blocked, not silently dropped.
3. **Escalation.** When a query needs a decision beyond the agent's authority (per spec 7.3/7.4), the agent calls `request_human_approval`, which creates a pending `ApprovalRequest` and tells the parent staff will follow up.
4. **Staff review.** Admission staff open `/admin`, see pending approvals and all cases, and approve or reject. Approving an `admission_decision` drives the real state machine transition; approving a `fee_exception` records the extension on the student record.

## Important edge cases (and what currently handles them)

| Edge case | Handling |
|---|---|
| Parent asks about a student whose phone doesn't match the record | `query_applicant_status` returns `{"status": "verification_failed"}`, never case data |
| Student has an active extension and a reminder of type `document_overdue`/`fee_overdue` is requested | Reminder is recorded as `blocked=True`, not sent |
| Agent tries to loop on tool calls indefinitely | `run_agent_turn` caps at `max_tool_iterations` (default 6) and falls back to "I need to check with our admission staff..." |
| Invalid state transition attempted (including from a terminal state) | `transition()` raises `InvalidTransitionError` |
| Document text contains a long digit run (possible government ID) | Masked to `XXXXXX` + last 4 digits before storage |

## Known limitations and future improvements

See "Proposed" list above, plus:
- No retry/backoff around the real Anthropic API call in `run_agent_turn` when `client=None`.
- No rate limiting or abuse protection on `/chat`.
- The evaluation harness scripts a fake model client to behave correctly — it does not grade the real Claude model's live behavior. Live evaluation is future work.
