from admission_agent.approvals import create_approval_request
from admission_agent.state_machine import ApplicationState


def test_chat_endpoint_returns_reply(client, sample_student, monkeypatch):
    monkeypatch.setattr("admission_agent.api.run_agent_turn", lambda db, student_id, message, parent_phone, **kw: "mocked reply")
    response = client.post("/chat", json={"student_id": sample_student.id, "message": "hi", "parent_phone": sample_student.parent.phone})
    assert response.status_code == 200
    assert response.json() == {"reply": "mocked reply"}


def test_chat_endpoint_passes_parent_phone_through(client, sample_student, monkeypatch):
    received = {}

    def fake_run_agent_turn(db, student_id, message, parent_phone, **kw):
        received["parent_phone"] = parent_phone
        return "ok"

    monkeypatch.setattr("admission_agent.api.run_agent_turn", fake_run_agent_turn)
    client.post("/chat", json={"student_id": sample_student.id, "message": "hi", "parent_phone": "0000000000"})
    assert received["parent_phone"] == "0000000000"


def test_admin_approvals_lists_pending(client, db_session, sample_student):
    create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.get("/admin/approvals")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_decide_approval_resolves_it(client, db_session, sample_student):
    sample_student.state = ApplicationState.WAITING_FOR_ADMISSION_DECISION.value
    db_session.commit()
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved", "resolved_by": "divya@school.example"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["resolved_by"] == "divya@school.example"


def test_admin_cases_lists_students(client, sample_student):
    response = client.get("/admin/cases")
    assert response.status_code == 200
    assert any(c["id"] == sample_student.id for c in response.json())


def test_admin_approvals_rejects_missing_auth(client):
    client.headers.pop("Authorization", None)
    response = client.get("/admin/approvals")
    assert response.status_code == 401


def test_admin_cases_rejects_missing_auth(client):
    client.headers.pop("Authorization", None)
    response = client.get("/admin/cases")
    assert response.status_code == 401


def test_admin_decide_rejects_missing_auth(client, db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    client.headers.pop("Authorization", None)
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert response.status_code == 401


def test_admin_decide_unknown_approval_id_returns_404(client):
    response = client.post("/admin/approvals/999999/decide", json={"decision": "approved"})
    assert response.status_code == 404


def test_admin_decide_already_resolved_returns_409(client, db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    first = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "rejected"})
    assert first.status_code == 200
    second = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert second.status_code == 409


def test_admin_decide_unknown_action_type_returns_400(client, db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "seat_allocation", {}, "staff request")
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert response.status_code == 400


def test_admin_decide_invalid_state_transition_returns_409(client, db_session, sample_student):
    req = create_approval_request(db_session, sample_student.id, "admission_decision", {"event": "officer_approves"}, "ready")
    response = client.post(f"/admin/approvals/{req.id}/decide", json={"decision": "approved"})
    assert response.status_code == 409
