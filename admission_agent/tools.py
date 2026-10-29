import re
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from admission_agent.approvals import create_approval_request
from admission_agent.knowledge_base import load_knowledge_base, search_knowledge_base
from admission_agent.models import CalendarBooking, Document, Parent, Reminder, Student

_MASK_PATTERN = re.compile(r"\d(?:[ -]?\d){9,}")

_OVERDUE_WORDING_PATTERN = re.compile(r"overdue|penalty|late fee|failure to (submit|pay)", re.IGNORECASE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _mask_long_digits(text: str) -> str:
    def _mask(match: re.Match) -> str:
        digits_only = re.sub(r"[ -]", "", match.group(0))
        return "XXXXXX" + digits_only[-4:]

    return _MASK_PATTERN.sub(_mask, text)


def _parse_slot_datetime(slot_datetime) -> datetime:
    if isinstance(slot_datetime, datetime):
        return slot_datetime
    return datetime.fromisoformat(slot_datetime)


def search_knowledge_base_tool(db: Session, query: str) -> list[dict]:
    kb = load_knowledge_base()
    return search_knowledge_base(query, kb)


def query_applicant_status(db: Session, student_id: int, parent_phone: str) -> dict:
    student = db.query(Student).filter_by(id=student_id).one()
    parent = db.query(Parent).filter_by(id=student.parent_id).one()
    if parent.phone != parent_phone:
        return {"status": "verification_failed"}
    return {"status": student.state, "name": student.name, "grade_applied": student.grade_applied}


def send_whatsapp_reminder(db: Session, student_id: int, message: str, reminder_type: str) -> dict:
    student = db.query(Student).filter_by(id=student_id).one()

    is_overdue_type = reminder_type in ("document_overdue", "fee_overdue")
    has_overdue_wording = bool(_OVERDUE_WORDING_PATTERN.search(message))
    has_active_extension = student.extension_granted_until is not None and student.extension_granted_until >= date.today()

    if (is_overdue_type or has_overdue_wording) and has_active_extension:
        reminder = Reminder(
            student_id=student_id,
            message=message,
            reminder_type=reminder_type,
            blocked=True,
            block_reason="active_extension",
        )
        db.add(reminder)
        db.commit()
        return {"sent": False, "reason": "active_extension"}

    reminder = Reminder(
        student_id=student_id,
        message=message,
        reminder_type=reminder_type,
        sent_at=_utcnow(),
    )
    db.add(reminder)
    db.commit()
    return {"sent": True}


def parse_uploaded_document(db: Session, student_id: int, doc_type: str, raw_text: str) -> dict:
    masked_text = _mask_long_digits(raw_text)
    document = Document(
        student_id=student_id,
        doc_type=doc_type,
        status="valid",
        raw_text=masked_text,
        parsed_data=masked_text,
    )
    db.add(document)
    db.commit()
    return {"doc_type": doc_type, "masked_text": masked_text}


def book_interview_slot(db: Session, student_id: int, slot_datetime) -> dict:
    parsed_slot = _parse_slot_datetime(slot_datetime)
    booking = CalendarBooking(student_id=student_id, slot_datetime=parsed_slot)
    db.add(booking)
    db.commit()
    return {"booked": True, "slot": parsed_slot.isoformat()}


def add_parent_to_whatsapp_group(db: Session, student_id: int) -> dict:
    student = db.query(Student).filter_by(id=student_id).one()
    student.added_to_group = True
    db.commit()
    return {"added": True}


def request_human_approval(db: Session, student_id: int, action_type: str, payload: dict, reason: str) -> dict:
    request = create_approval_request(db, student_id, action_type, payload, reason)
    return {"approval_id": request.id, "status": "pending"}


TOOL_SCHEMAS = [
    {
        "name": "search_knowledge_base",
        "description": "Search the school's knowledge base (fees, eligibility, FAQs) for information relevant to a parent's question.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "query_applicant_status",
        "description": "Look up a student's application status. Requires the parent's phone number on file to match before any case data is returned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "parent_phone": {"type": "string"},
            },
            "required": ["student_id", "parent_phone"],
        },
    },
    {
        "name": "send_whatsapp_reminder",
        "description": "Send a WhatsApp reminder to the parent. Overdue-type reminders are automatically blocked if the student has an active staff-granted extension.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "message": {"type": "string"},
                "reminder_type": {"type": "string", "enum": ["generic", "document_overdue", "fee_overdue"]},
            },
            "required": ["student_id", "message", "reminder_type"],
        },
    },
    {
        "name": "parse_uploaded_document",
        "description": "Parse an uploaded document's text, masking any long government-ID-like digit sequences before storing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "doc_type": {"type": "string"},
                "raw_text": {"type": "string"},
            },
            "required": ["student_id", "doc_type", "raw_text"],
        },
    },
    {
        "name": "book_interview_slot",
        "description": "Book a parent-principal interview slot on the school calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "slot_datetime": {"type": "string", "description": "ISO 8601 datetime"},
            },
            "required": ["student_id", "slot_datetime"],
        },
    },
    {
        "name": "add_parent_to_whatsapp_group",
        "description": "Add the parent's phone number to the school's WhatsApp group.",
        "input_schema": {
            "type": "object",
            "properties": {"student_id": {"type": "integer"}},
            "required": ["student_id"],
        },
    },
    {
        "name": "request_human_approval",
        "description": "Request human (admission staff) approval for a high-risk action, such as an admission decision or a fee exception. This is the only way such actions can take effect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "action_type": {"type": "string", "enum": ["admission_decision", "fee_exception"]},
                "payload": {"type": "object"},
                "reason": {"type": "string"},
            },
            "required": ["student_id", "action_type", "payload", "reason"],
        },
    },
]


def _search_knowledge_base_dispatch(db: Session, query: str) -> list[dict]:
    return search_knowledge_base_tool(db, query)


TOOL_DISPATCH = {
    "search_knowledge_base": _search_knowledge_base_dispatch,
    "query_applicant_status": query_applicant_status,
    "send_whatsapp_reminder": send_whatsapp_reminder,
    "parse_uploaded_document": parse_uploaded_document,
    "book_interview_slot": book_interview_slot,
    "add_parent_to_whatsapp_group": add_parent_to_whatsapp_group,
    "request_human_approval": request_human_approval,
}
