from datetime import date, timedelta

from admission_agent.models import Document
from admission_agent.tools import (
    book_interview_slot,
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


def test_parse_uploaded_document_does_not_store_unmasked_text_anywhere(db_session, sample_student):
    parse_uploaded_document(db_session, sample_student.id, "birth_certificate", "ID 123456789012 issued 2015")
    document = db_session.query(Document).filter_by(student_id=sample_student.id).one()
    assert "123456789012" not in document.raw_text
    assert "123456789012" not in document.parsed_data


def test_parse_uploaded_document_masks_space_separated_digit_groups(db_session, sample_student):
    result = parse_uploaded_document(db_session, sample_student.id, "id_card", "Aadhaar 1234 5678 9012, card 4111 1111 1111 1111")
    assert "1234 5678 9012" not in result["masked_text"]
    assert "4111 1111 1111 1111" not in result["masked_text"]
    assert "9012" in result["masked_text"]
    assert "1111" in result["masked_text"]


def test_overdue_worded_reminder_blocked_regardless_of_reminder_type_label(db_session, sample_student):
    sample_student.extension_granted_until = date.today() + timedelta(days=5)
    db_session.commit()
    result = send_whatsapp_reminder(
        db_session, sample_student.id, "This is overdue — a penalty applies if you do not pay immediately.", "generic"
    )
    assert result == {"sent": False, "reason": "active_extension"}


def test_book_interview_slot_accepts_iso_string_datetime(db_session, sample_student):
    result = book_interview_slot(db_session, sample_student.id, "2026-11-05T10:00:00")
    assert result["booked"] is True
    assert result["slot"] == "2026-11-05T10:00:00"
