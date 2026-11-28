"""Pruebas de la carga de los modelos reales (churn y segmentación). Ejecutar con: pytest"""

import json

import pandas as pd
import pytest

import model_service
from conftest import VALID_CUSTOMER, customer
from schema import FIELD_NAMES

ROOT = model_service.ROOT
MODEL = "models/telco_churn_logistic.joblib"
MODEL_INFO = ROOT / "models" / "churn_model_info.json"
SEGMENTS_INFO = ROOT / "models" / "segments_info.json"


@pytest.fixture(autouse=True)
def fresh_models():
    """Cada prueba carga los modelos de nuevo; al final se vuelve al modelo de prueba."""
    model_service.reset()
    yield
    model_service.reset()


@pytest.fixture
def real_model(monkeypatch):
    monkeypatch.setenv("MODEL_PATH", MODEL)
    return model_service.load_models()


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- Modelo real ---------------------------------------------------------


def test_real_model_uses_the_threshold_of_the_model_team(real_model):
    expected = json.loads(MODEL_INFO.read_text(encoding="utf-8"))["threshold"]

    assert real_model["version"] == "telco_churn_logistic"
    assert real_model["threshold"] == expected == 0.325


def test_real_model_predicts_through_the_api(client, real_model):
    response = client.post("/predict", json=VALID_CUSTOMER)
    body = response.get_json()

    assert response.status_code == 200
    assert body["model_version"] == "telco_churn_logistic"
    assert body["churn"] == (body["probability"] >= 0.325)
    assert client.get("/health").get_json()["model_version"] == "telco_churn_logistic"


def test_churn_uses_the_threshold_from_the_json(tmp_path, monkeypatch, real_model):
    # Mismo cliente, dos umbrales: lo único que cambia la respuesta es el JSON
    probability = model_service.predict_customer(VALID_CUSTOMER)["probability"]
    info = json.loads(MODEL_INFO.read_text(encoding="utf-8"))

    for threshold, expected in [(probability, True), (min(probability + 0.01, 0.99), False)]:
        monkeypatch.setenv("MODEL_INFO_PATH", str(write_json(tmp_path / "info.json", {**info, "threshold": threshold})))
        model_service.reset()
        assert model_service.predict_customer(VALID_CUSTOMER)["churn"] is expected


def test_api_matches_the_model_team_output_for_the_whole_dataset(real_model):
    # Para los 7,043 clientes, la API debe dar:
    # - el mismo segmento que el CSV del equipo de Modelos, y
    # - la misma probabilidad que el modelo con los conteos que calcula Modelos
    #   (src/modeling/feature_engineering.py). Así se comprueba que los conteos de la API y de la
    #   página (los dos cuentan los "Yes") son los mismos del entrenamiento.
    # La probabilidad no se compara con el CSV: ese archivo trae puntuaciones out-of-fold (cada
    # cliente, con un modelo que no lo vio), no las del modelo final que usa la API.
    from src.modeling.feature_engineering import build_model_features

    clean = pd.read_csv(ROOT / "data" / "processed" / "telco_churn_clean.csv")
    expected = pd.read_csv(ROOT / "data" / "output" / "telco_churn_model_output.csv").set_index("customerID")
    team_features = build_model_features(clean)[FIELD_NAMES]
    team_probabilities = real_model["model"].predict_proba(team_features)[:, 1].round(2)

    customers = model_service.add_service_counts(clean)[FIELD_NAMES].to_dict("records")
    results = model_service.predict_many(customers)

    assert [r["segment"]["name"] for r in results] == expected.loc[clean["customerID"], "segment_name"].tolist()
    assert [r["probability"] for r in results] == team_probabilities.tolist()
    assert all(r["churn"] == (r["probability"] >= 0.325) for r in results)


def test_predict_many_equals_one_by_one(real_model):
    customers = [VALID_CUSTOMER, customer(tenure=60, Contract="Two year", SecuritySupportCount=3)]
    assert model_service.predict_many(customers) == [model_service.predict_customer(c) for c in customers]
    assert model_service.predict_many([]) == []


# --- Segmentación -------------------------------------------------------


def test_segment_comes_with_its_name(client):
    names = {s["name"] for s in json.loads(SEGMENTS_INFO.read_text(encoding="utf-8"))["segments"]}
    segment = client.post("/predict", json=VALID_CUSTOMER).get_json()["segment"]

    assert list(segment) == ["id", "name", "description"]
    assert segment["id"] in range(4)
    assert segment["name"] in names


def test_segments_follow_the_four_kmeans_columns():
    phone_only = customer(
        tenure=40, Contract="Two year", MonthlyCharges=20.15, InternetService="No", SecuritySupportCount=0
    )
    fiber_new = customer(tenure=5, Contract="Month-to-month", MonthlyCharges=85.30, InternetService="Fiber optic")
    assert model_service.predict_customer(phone_only)["segment"]["name"] == "Telefonía estable"
    assert model_service.predict_customer(fiber_new)["segment"]["name"] == "Fibra en riesgo"


def test_segment_is_null_without_segments_model(client, monkeypatch, tmp_path):
    monkeypatch.setenv("SEGMENTS_MODEL_PATH", str(tmp_path / "no_existe.joblib"))
    model_service.reset()

    response = client.post("/predict", json=VALID_CUSTOMER)
    assert response.status_code == 200
    assert response.get_json()["segment"] is None


def test_segments_info_must_match_the_model(monkeypatch, tmp_path):
    info = json.loads(SEGMENTS_INFO.read_text(encoding="utf-8"))
    info["segments"] = info["segments"][:3]  # falta el segmento 3
    monkeypatch.setenv("SEGMENTS_INFO_PATH", str(write_json(tmp_path / "segments.json", info)))

    with pytest.raises(model_service.ModelError, match="no coincide"):
        model_service.load_models()


@pytest.mark.parametrize(
    "columns, message",
    [(None, '"columns"'), (["tenure", "TotalCharges"], "no están en el contrato")],
)
def test_segments_info_needs_contract_columns(monkeypatch, tmp_path, columns, message):
    info = json.loads(SEGMENTS_INFO.read_text(encoding="utf-8"))
    info["columns"] = columns
    monkeypatch.setenv("SEGMENTS_INFO_PATH", str(write_json(tmp_path / "segments.json", info)))

    with pytest.raises(model_service.ModelError, match=message):
        model_service.load_models()


# --- Errores de configuración: la API no arranca y dice por qué --------------


def test_real_model_without_info_file_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_PATH", MODEL)
    monkeypatch.setenv("MODEL_INFO_PATH", str(tmp_path / "no_existe.json"))

    with pytest.raises(model_service.ModelError, match="No se encontró"):
        model_service.load_models()


@pytest.mark.parametrize("threshold", [None, "0.325", 0, 1, 1.5, True])
def test_invalid_threshold_fails(monkeypatch, tmp_path, threshold):
    info = json.loads(MODEL_INFO.read_text(encoding="utf-8"))
    info["threshold"] = threshold
    monkeypatch.setenv("MODEL_PATH", MODEL)
    monkeypatch.setenv("MODEL_INFO_PATH", str(write_json(tmp_path / "info.json", info)))

    with pytest.raises(model_service.ModelError, match="threshold"):
        model_service.load_models()


def test_info_with_other_columns_fails(monkeypatch, tmp_path):
    info = json.loads(MODEL_INFO.read_text(encoding="utf-8"))
    info["input_columns"] = info["input_columns"][:-1]
    monkeypatch.setenv("MODEL_PATH", MODEL)
    monkeypatch.setenv("MODEL_INFO_PATH", str(write_json(tmp_path / "info.json", info)))

    with pytest.raises(model_service.ModelError, match="columnas"):
        model_service.load_models()


def test_missing_model_file_uses_demo_or_fails_with_require_model(monkeypatch, caplog):
    monkeypatch.setenv("MODEL_PATH", "models/no_existe.joblib")
    assert model_service.load_models()["version"] == "demo"
    assert "no existe" in caplog.text

    model_service.reset()
    monkeypatch.setenv("REQUIRE_MODEL", "1")
    with pytest.raises(model_service.ModelError, match="no existe"):
        model_service.load_models()


def test_missing_module_explains_the_problem(monkeypatch):
    # Así falla joblib cuando el modelo necesita un módulo que no está instalado
    def load_without_module(path):
        raise ModuleNotFoundError("No module named 'src'", name="src")

    monkeypatch.setenv("MODEL_PATH", MODEL)
    monkeypatch.setattr(model_service.joblib, "load", load_without_module)

    with pytest.raises(model_service.ModelError, match="falta el módulo src"):
        model_service.load_models()
