from admission_agent.approvals import create_approval_request
from admission_agent.state_machine import ApplicationState


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
    sample_student.state = ApplicationState.WAITING_FOR_ADMISSION_DECISION.value
    db_session.commit()
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_admin_cases_lists_students(client, sample_student):
    response = client.get("/admin/cases")
    assert response.status_code == 200
    assert any(c["id"] == sample_student.id for c in response.json())
