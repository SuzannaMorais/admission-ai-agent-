import pytest

from admission_agent.approvals import (
    ApprovalAlreadyResolvedError,
    create_approval_request,
    list_pending_approvals,
    resolve_approval,
)
from admission_agent.state_machine import ApplicationState


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


def test_resolving_an_already_resolved_approval_raises_and_does_not_reapply(db_session, sample_student):
    original_state = sample_student.state
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    resolve_approval(db_session, req.id, "rejected")

    with pytest.raises(ApprovalAlreadyResolvedError):
        resolve_approval(db_session, req.id, "approved")

    db_session.refresh(sample_student)
    assert sample_student.state == original_state


def test_resolving_an_unknown_action_type_raises(db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "seat_allocation", {}, "staff request")
    with pytest.raises(ValueError):
        resolve_approval(db_session, req.id, "approved")


def test_resolve_approval_records_who_resolved_it(db_session, sample_student):
    sample_student.state = ApplicationState.WAITING_FOR_ADMISSION_DECISION.value
    db_session.commit()
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    resolved = resolve_approval(db_session, req.id, "approved", resolved_by="divya@school.example")
    assert resolved.resolved_by == "divya@school.example"
