"""Pruebas de POST /predict y de la validación (schema.py). Ejecutar con: pytest"""

import json

import pytest

from conftest import VALID_CUSTOMER, customer


# --- Respuestas correctas ------------------------------------------------


def test_predict_returns_the_contract_fields(client):
    response = client.post("/predict", json=VALID_CUSTOMER)
    body = response.get_json()

    assert response.status_code == 200
    assert list(body) == ["churn", "probability", "risk_level", "segment", "model_version"]
    assert isinstance(body["churn"], bool)
    assert 0 <= body["probability"] <= 1
    assert body["probability"] == round(body["probability"], 2)
    assert body["risk_level"] in {"low", "medium", "high"}
    assert body["model_version"] == "demo"


def test_new_customer_is_valid(client):
    # Un cliente recién llegado: tenure 0
    response = client.post("/predict", json=customer(tenure=0))
    assert response.status_code == 200


def test_customer_without_internet_is_valid(client):
    response = client.post(
        "/predict", json=customer(InternetService="No", SecuritySupportCount=0, StreamingServicesCount=0)
    )
    assert response.status_code == 200


def test_service_counts_accept_their_whole_range(client):
    for security, streaming in [(0, 0), (4, 2)]:
        response = client.post(
            "/predict", json=customer(SecuritySupportCount=security, StreamingServicesCount=streaming)
        )
        assert response.status_code == 200


def test_risk_level_matches_the_rounded_probability():
    import model_service

    assert model_service.risk_level(0.29) == "low"
    assert model_service.risk_level(0.30) == "medium"
    assert model_service.risk_level(0.59) == "medium"
    assert model_service.risk_level(0.60) == "high"


def test_health_reports_the_model_version(client):
    assert client.get("/health").get_json()["model_version"] == "demo"


# --- Errores 400 con el campo culpable -----------------------------------


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"Contract": ...}, "Contract"),                          # falta un campo
        ({"Contract": "Mensual"}, "Contract"),                    # valor no permitido
        ({"gender": "female"}, "gender"),                         # mayúsculas distintas
        ({"SeniorCitizen": "1"}, "SeniorCitizen"),                # texto en vez de número
        ({"SeniorCitizen": True}, "SeniorCitizen"),               # booleano en vez de 0/1
        ({"tenure": 1.5}, "tenure"),                              # no es entero
        ({"tenure": -1}, "tenure"),                               # negativo
        ({"tenure": True}, "tenure"),                             # booleano
        ({"MonthlyCharges": 0}, "MonthlyCharges"),                # debe ser mayor que 0
        ({"MonthlyCharges": "29.85"}, "MonthlyCharges"),          # texto
        ({"customerID": "7590-VHVEG"}, "customerID"),             # campo fuera del contrato
        ({"tenure": 10**400}, "tenure"),                          # entero gigante (no cabe en float)
        ({"MonthlyCharges": 10**400}, "MonthlyCharges"),
        ({"SecuritySupportCount": ...}, "SecuritySupportCount"),  # la página no lo calculó
        ({"SecuritySupportCount": 5}, "SecuritySupportCount"),    # son 4 servicios como máximo
        ({"SecuritySupportCount": -1}, "SecuritySupportCount"),
        ({"SecuritySupportCount": 1.5}, "SecuritySupportCount"),
        ({"StreamingServicesCount": 3}, "StreamingServicesCount"),  # son 2 servicios como máximo
        ({"StreamingServicesCount": "1"}, "StreamingServicesCount"),
        # Campos que ya no usa el modelo: la página no debe enviarlos
        ({"TotalCharges": 29.85}, "TotalCharges"),
        ({"PhoneService": "No"}, "PhoneService"),
        ({"OnlineBackup": "Yes"}, "OnlineBackup"),
    ],
)
def test_invalid_customer_returns_400_with_field(client, changes, field):
    response = client.post("/predict", json=customer(**changes))
    body = response.get_json()

    assert response.status_code == 400
    assert body["field"] == field
    assert body["error"]  # mensaje en español, no vacío


@pytest.mark.parametrize(
    "counts, field",
    [
        ({"SecuritySupportCount": 1, "StreamingServicesCount": 0}, "SecuritySupportCount"),
        ({"SecuritySupportCount": 0, "StreamingServicesCount": 2}, "StreamingServicesCount"),
    ],
)
def test_no_internet_requires_zero_service_counts(client, counts, field):
    # Los servicios que se cuentan son de internet: sin internet, los dos conteos son 0
    response = client.post("/predict", json=customer(InternetService="No", **counts))
    assert response.status_code == 400
    assert response.get_json()["field"] == field


def test_nan_is_rejected(client):
    # Python acepta NaN dentro de un JSON; la API no debe dejarlo pasar al modelo
    raw = json.dumps(customer()).replace('"MonthlyCharges": 29.85', '"MonthlyCharges": NaN')
    response = client.post("/predict", data=raw, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["field"] == "MonthlyCharges"


@pytest.mark.parametrize("body", ["esto no es JSON", "[1, 2, 3]", "null"])
def test_body_that_is_not_a_json_object_returns_400(client, body):
    response = client.post("/predict", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["field"] is None


def test_get_on_predict_returns_405(client):
    assert client.get("/predict").status_code == 405
