def test_openapi_schema_is_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Network Control API"


def test_protected_admin_endpoint_requires_authentication(client):
    response = client.get("/api/admin")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
