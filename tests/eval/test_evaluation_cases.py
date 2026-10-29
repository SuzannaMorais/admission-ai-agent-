from admission_agent.agent import run_agent_turn
from admission_agent.knowledge_base import load_knowledge_base
from admission_agent.models import ApprovalRequest
from admission_agent.tools import query_applicant_status
from tests.support.fake_anthropic import FakeAnthropicClient, text_response, tool_use_response


def _kb_entry(entry_id: str) -> dict:
    kb = load_knowledge_base()
    return next(e for e in kb if e["id"] == entry_id)


def test_case_1_fee_enquiry(db_session, sample_student):
    fee_entry = _kb_entry("fee-grade-3")
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "admission fee for grade 3"}),
        text_response(f"Here are the details: {fee_entry['content']}"),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "What's the admission fee for grade 3?", sample_student.parent.phone, client=client)
    assert "25,000" in reply


def test_case_2_age_eligibility(db_session, sample_student):
    eligibility_entry = _kb_entry("eligibility-grade-1")
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "grade 1 age eligibility"}),
        text_response(f"Here's what I found: {eligibility_entry['content']}"),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "Is my child eligible for grade 1?", sample_student.parent.phone, client=client)
    assert "eligible" in reply.lower()
    assert eligibility_entry["content"] in reply


def test_case_3_admission_deadline(db_session, sample_student):
    deadline_entry = _kb_entry("fee-deadline")
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "admission fee deadline"}),
        text_response(f"Reminder: {deadline_entry['content']}"),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "When is the admission fee deadline?", sample_student.parent.phone, client=client)
    assert "30 November 2026" in reply


def test_case_4_student_status_requires_verification(db_session, sample_student):
    result = query_applicant_status(db_session, sample_student.id, parent_phone="0000000000")
    assert result == {"status": "verification_failed"}


def test_case_5_uncertain_query_escalates_to_human(db_session, sample_student):
    client = FakeAnthropicClient([
        tool_use_response(
            "request_human_approval",
            {
                "student_id": sample_student.id,
                "action_type": "admission_decision",
                "payload": {"event": "officer_approves"},
                "reason": "parent asked an out-of-scope question",
            },
        ),
        text_response("I'm not certain about that, so I've asked our admission staff to follow up with you."),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "Can you just approve my child right now?", sample_student.parent.phone, client=client)

    pending = db_session.query(ApprovalRequest).filter_by(student_id=sample_student.id, status="pending").all()
    assert len(pending) == 1
    assert "staff" in reply.lower()
