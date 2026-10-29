from datetime import date, timedelta

from admission_agent.tools import (
    parse_uploaded_document,
    query_applicant_status,
    request_human_approval,
    send_whatsapp_reminder,
)


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
