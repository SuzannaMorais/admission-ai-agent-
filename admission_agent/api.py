import json
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from admission_agent.agent import run_agent_turn
from admission_agent.approvals import list_pending_approvals, resolve_approval
from admission_agent.db import get_db
from admission_agent.models import Student

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html")


class ChatRequest(BaseModel):
    student_id: int
    message: str


class DecideRequest(BaseModel):
    decision: str
    resolver_note: str | None = None


@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    reply = run_agent_turn(db, request.student_id, request.message)
    return {"reply": reply}


@app.get("/admin/approvals")
def admin_approvals(db: Session = Depends(get_db)):
    approvals = list_pending_approvals(db)
    return [
        {
            "id": a.id,
            "student_id": a.student_id,
            "action_type": a.action_type,
            "payload": json.loads(a.payload),
            "reason": a.reason,
            "status": a.status,
        }
        for a in approvals
    ]


@app.post("/admin/approvals/{approval_id}/decide")
def admin_decide_approval(approval_id: int, request: DecideRequest, db: Session = Depends(get_db)):
    resolved = resolve_approval(db, approval_id, request.decision, resolver_note=request.resolver_note)
    return {
        "id": resolved.id,
        "student_id": resolved.student_id,
        "action_type": resolved.action_type,
        "payload": json.loads(resolved.payload),
        "reason": resolved.reason,
        "status": resolved.status,
    }


@app.get("/admin/cases")
def admin_cases(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return [
        {"id": s.id, "name": s.name, "grade_applied": s.grade_applied, "state": s.state}
        for s in students
    ]
