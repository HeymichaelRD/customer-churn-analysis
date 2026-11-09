"""Carga el modelo y calcula el riesgo de abandono de un cliente.

- Si existe el archivo de MODEL_PATH (variable del .env), usa ese modelo: el del equipo de Modelos.
- Si no existe, usa un MODELO DE PRUEBA entrenado aquí mismo con data/raw. Sirve para que la
  web funcione mientras llega el modelo real; sus resultados son solo de ejemplo.

El modelo se carga una sola vez, la primera vez que se necesita, y se reutiliza.
"""

import os
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from schema import FIELD_NAMES

ROOT = Path(__file__).resolve().parents[2]
RAW_DATA = ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
DEMO_VERSION = "demo"

# Niveles de riesgo provisionales (ver docs/plan-api-web.md). Se ajustan con el equipo de Modelos.
MEDIUM_FROM = 0.30
HIGH_FROM = 0.60
# Desde qué probabilidad se responde churn = true. Provisional, igual que los niveles.
CHURN_THRESHOLD = 0.50

NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL = [name for name in FIELD_NAMES if name not in NUMERIC]


def risk_level(probability):
    if probability >= HIGH_FROM:
        return "high"
    if probability >= MEDIUM_FROM:
        return "medium"
    return "low"


def _train_demo_model():
    # Modelo de prueba: regresión logística sobre las columnas originales del dataset.
    # Recibe los datos igual que el modelo real (un Pipeline con las 19 columnas originales).
    df = pd.read_csv(RAW_DATA)
    # TotalCharges viene como texto con 11 blancos (clientes con tenure 0): se dejan en 0.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    X, y = df[FIELD_NAMES], (df["Churn"] == "Yes").astype(int)

    preprocess = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("model", LogisticRegression(max_iter=1000))]).fit(X, y)


@lru_cache(maxsize=1)
def load_model():
    """Devuelve (modelo, versión). Se ejecuta una sola vez gracias a lru_cache."""
    model_path = os.environ.get("MODEL_PATH")
    if model_path:
        path = Path(model_path)
        path = path if path.is_absolute() else ROOT / path
        if path.exists():
            return joblib.load(path), path.stem
    return _train_demo_model(), DEMO_VERSION


def model_version():
    return load_model()[1]


def predict_customer(customer):
    """Predice un cliente ya validado (ver schema.validate_customer)."""
    model, version = load_model()
    row = pd.DataFrame([customer], columns=FIELD_NAMES)
    # Se redondea antes de clasificar para que el nivel coincida con el número que ve el usuario
    # (si no, 0.597 se mostraría como 0.60 pero con riesgo "medium").
    probability = round(float(model.predict_proba(row)[0, 1]), 2)
    return {
        "churn": probability >= CHURN_THRESHOLD,
        "probability": probability,
        "risk_level": risk_level(probability),
        "model_version": version,
    }
