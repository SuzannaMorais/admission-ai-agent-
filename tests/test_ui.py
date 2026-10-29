def test_root_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Send" in response.content


def test_root_page_collects_and_sends_parent_phone(client):
    response = client.get("/")
    assert b"parentPhone" in response.content
    assert b"parent_phone" in response.content


def test_admin_page_loads(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Approve" in response.content


def test_admin_page_does_not_build_rows_with_unsafe_innerHTML(client):
    response = client.get("/admin")
    html = response.text
    assert "tr.innerHTML" not in html
    assert "textContent" in html


def test_admin_page_renders_approval_payload(client):
    response = client.get("/admin")
    assert "payload" in response.text
