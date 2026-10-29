import json
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from admission_agent.models import ApprovalRequest, Student
from admission_agent.state_machine import ApplicationState, transition


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_approval_request(db: Session, student_id: int, action_type: str, payload: dict, reason: str) -> ApprovalRequest:
    request = ApprovalRequest(
        student_id=student_id,
        action_type=action_type,
        payload=json.dumps(payload),
        status="pending",
        reason=reason,
    )
    db.add(request)
    db.commit()
    return request


def list_pending_approvals(db: Session) -> list[ApprovalRequest]:
    return db.query(ApprovalRequest).filter_by(status="pending").all()


def resolve_approval(db: Session, approval_id: int, decision: str, resolver_note: str | None = None) -> ApprovalRequest:
    if decision not in ("approved", "rejected"):
        raise ValueError(f"Invalid decision: {decision!r}")

    request = db.query(ApprovalRequest).filter_by(id=approval_id).one()
    payload = json.loads(request.payload)

    if decision == "approved":
        student = db.query(Student).filter_by(id=request.student_id).one()
        if request.action_type == "admission_decision":
            new_state = transition(ApplicationState(student.state), payload["event"])
            student.state = new_state.value
        elif request.action_type == "fee_exception":
            student.extension_note = payload["note"]
            student.extension_granted_until = date.fromisoformat(payload["until"])

    request.status = decision
    request.resolved_at = _utcnow()
    request.resolver_note = resolver_note
    db.commit()
    return request
