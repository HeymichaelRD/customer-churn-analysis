"""Pruebas de POST /predict y de la validación (schema.py). Ejecutar con: pytest"""

import json

import pytest

from app import app

# El primer cliente del dataset: es el ejemplo del contrato en el README.
VALID_CUSTOMER = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 1,
    "PhoneService": "No",
    "MultipleLines": "No phone service",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 29.85,
    "TotalCharges": 29.85,
}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def customer(**changes):
    """Copia del cliente válido con algunos campos cambiados (o quitados, si el valor es ...)."""
    data = {**VALID_CUSTOMER, **changes}
    return {k: v for k, v in data.items() if v is not ...}


# --- Respuestas correctas ------------------------------------------------


def test_predict_returns_the_contract_fields(client):
    response = client.post("/predict", json=VALID_CUSTOMER)
    body = response.get_json()

    assert response.status_code == 200
    assert list(body) == ["churn", "probability", "risk_level", "model_version"]
    assert isinstance(body["churn"], bool)
    assert 0 <= body["probability"] <= 1
    assert body["probability"] == round(body["probability"], 2)
    assert body["risk_level"] in {"low", "medium", "high"}
    assert body["model_version"] == "demo"


def test_new_customer_with_zero_charges_is_valid(client):
    # Un cliente recién llegado: tenure 0 y TotalCharges 0 (así lo pide el contrato)
    response = client.post("/predict", json=customer(tenure=0, TotalCharges=0))
    assert response.status_code == 200


def test_customer_without_internet_is_valid(client):
    no_internet = {name: "No internet service" for name in
                   ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                    "TechSupport", "StreamingTV", "StreamingMovies"]}
    response = client.post(
        "/predict",
        json=customer(PhoneService="Yes", MultipleLines="No", InternetService="No", **no_internet),
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
        ({"TotalCharges": -5}, "TotalCharges"),                   # negativo
        ({"customerID": "7590-VHVEG"}, "customerID"),             # campo fuera del contrato
        ({"tenure": 10**400}, "tenure"),                          # entero gigante (no cabe en float)
        ({"MonthlyCharges": 10**400}, "MonthlyCharges"),
        ({"TotalCharges": 10**400}, "TotalCharges"),
        ({"MultipleLines": "No"}, "MultipleLines"),               # sin teléfono pero con líneas
        ({"PhoneService": "Yes"}, "MultipleLines"),               # con teléfono pero "No phone service"
        ({"OnlineSecurity": "No internet service"}, "OnlineSecurity"),  # con internet
    ],
)
def test_invalid_customer_returns_400_with_field(client, changes, field):
    response = client.post("/predict", json=customer(**changes))
    body = response.get_json()

    assert response.status_code == 400
    assert body["field"] == field
    assert body["error"]  # mensaje en español, no vacío


def test_no_internet_requires_no_internet_service(client):
    # Con teléfono, para que el único problema sea el de los servicios de internet
    response = client.post(
        "/predict", json=customer(PhoneService="Yes", MultipleLines="No", InternetService="No")
    )
    assert response.status_code == 400
    assert response.get_json()["field"] == "OnlineSecurity"


def test_customer_needs_phone_or_internet(client):
    no_internet = {name: "No internet service" for name in
                   ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                    "TechSupport", "StreamingTV", "StreamingMovies"]}
    # Sin teléfono (como el cliente de ejemplo) y además sin internet: coherente campo a campo,
    # pero ese tipo de cliente no existe en los datos
    response = client.post("/predict", json=customer(InternetService="No", **no_internet))
    assert response.status_code == 400
    assert response.get_json()["field"] == "PhoneService"


def test_nan_is_rejected(client):
    # Python acepta NaN dentro de un JSON; la API no debe dejarlo pasar al modelo
    raw = json.dumps(customer()).replace("29.85}", "NaN}")
    response = client.post("/predict", data=raw, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["field"] == "TotalCharges"


@pytest.mark.parametrize("body", ["esto no es JSON", "[1, 2, 3]", "null"])
def test_body_that_is_not_a_json_object_returns_400(client, body):
    response = client.post("/predict", data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["field"] is None


def test_get_on_predict_returns_405(client):
    assert client.get("/predict").status_code == 405
