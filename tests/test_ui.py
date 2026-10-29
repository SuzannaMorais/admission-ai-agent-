def test_root_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Send" in response.content


def test_admin_page_loads(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Approve" in response.content
