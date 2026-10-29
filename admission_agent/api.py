import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from admission_agent.agent import run_agent_turn
from admission_agent.approvals import ApprovalAlreadyResolvedError, list_pending_approvals, resolve_approval
from admission_agent.db import get_db, init_db
from admission_agent.models import Student
from admission_agent.state_machine import InvalidTransitionError

init_db()

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def get_admin_token() -> str:
    return os.environ.get("ADMIN_TOKEN", "")


def require_admin(authorization: str | None = Header(default=None), expected_token: str = Depends(get_admin_token)) -> None:
    if not expected_token:
        raise HTTPException(status_code=503, detail="Admin auth not configured (set ADMIN_TOKEN)")
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Missing or invalid admin credentials")


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/admin")
def admin_page(request: Request, _: None = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin.html")


class ChatRequest(BaseModel):
    student_id: int
    message: str
    parent_phone: str


class DecideRequest(BaseModel):
    decision: str
    resolver_note: str | None = None
    resolved_by: str | None = None


def _approval_to_dict(approval) -> dict:
    return {
        "id": approval.id,
        "student_id": approval.student_id,
        "action_type": approval.action_type,
        "payload": json.loads(approval.payload),
        "reason": approval.reason,
        "status": approval.status,
        "resolved_by": approval.resolved_by,
    }


@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    reply = run_agent_turn(db, request.student_id, request.message, request.parent_phone)
    return {"reply": reply}


@app.get("/admin/approvals")
def admin_approvals(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    approvals = list_pending_approvals(db)
    return [_approval_to_dict(a) for a in approvals]


@app.post("/admin/approvals/{approval_id}/decide")
def admin_decide_approval(
    approval_id: int,
    request: DecideRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    try:
        resolved = resolve_approval(
            db,
            approval_id,
            request.decision,
            resolver_note=request.resolver_note,
            resolved_by=request.resolved_by,
        )
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ApprovalAlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _approval_to_dict(resolved)


@app.get("/admin/cases")
def admin_cases(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    students = db.query(Student).all()
    return [
        {"id": s.id, "name": s.name, "grade_applied": s.grade_applied, "state": s.state}
        for s in students
    ]
