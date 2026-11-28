"""Pruebas de la API de Flask. Ejecutar con: pytest"""


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert "model_version" in response.get_json()


def test_unknown_route_returns_json_error(client):
    response = client.get("/ruta-que-no-existe")

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_cors_allows_the_web_page(client):
    response = client.get("/health", headers={"Origin": "http://localhost:8000"})

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:8000"
