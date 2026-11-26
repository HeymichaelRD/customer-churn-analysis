"""Datos y fixtures compartidos por todas las pruebas. pytest carga este archivo solo."""

import os

import pytest

# Las pruebas empiezan siempre con el modelo de PRUEBA, aunque en la terminal estén definidas
# estas variables. Se borran aquí, antes de importar app (que carga los modelos al arrancar).
# Las pruebas del modelo real (test_models.py) las vuelven a poner con monkeypatch.
for _name in ["MODEL_PATH", "MODEL_INFO_PATH", "SEGMENTS_MODEL_PATH", "SEGMENTS_INFO_PATH", "REQUIRE_MODEL"]:
    os.environ.pop(_name, None)

from app import app  # noqa: E402  (va después de limpiar las variables)

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

INTERNET_ADDONS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]


def customer(**changes):
    """Copia del cliente válido con algunos campos cambiados (o quitados, si el valor es ...)."""
    data = {**VALID_CUSTOMER, **changes}
    return {k: v for k, v in data.items() if v is not ...}


@pytest.fixture
def client():
    """Cliente de prueba: llama a la API sin tener que encenderla."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
