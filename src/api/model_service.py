"""Carga el modelo y calcula el riesgo de abandono de uno o varios clientes.

- Si existe el archivo de MODEL_PATH (variable del .env), usa ese modelo: el del equipo de Modelos.
  Si al lado está models/model_info.json, de ahí salen la versión, el umbral y los niveles de riesgo.
- Si MODEL_PATH no está definida, o apunta a un archivo que no existe, usa un MODELO DE PRUEBA
  entrenado aquí mismo con data/raw (y lo avisa en el log). Con REQUIRE_MODEL=1 en el .env,
  un archivo que no existe es un error y la API no arranca: útil para la demo final.

El modelo se carga una sola vez (al arrancar la API, ver app.py) y se reutiliza.
"""

import json
import logging
import os
import threading
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from schema import FIELD_NAMES

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
RAW_DATA = ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
DEMO_VERSION = "demo"

# Valores provisionales (ver docs/plan-api-web.md). Si llega models/model_info.json, se usan los suyos.
DEFAULT_SETTINGS = {
    "version": DEMO_VERSION,
    "threshold": 0.50,  # desde qué probabilidad se responde churn = true
    "medium_from": 0.30,
    "high_from": 0.60,
}

NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL = [name for name in FIELD_NAMES if name not in NUMERIC]


class ModelError(Exception):
    """El modelo no se pudo cargar o no es compatible con el contrato."""


def _env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _train_demo_model():
    # Modelo de prueba: regresión logística sobre las columnas originales del dataset.
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


def _check_model(model, path):
    """Falla al cargar (y no en la primera predicción) si el modelo no sirve para la API."""
    if not hasattr(model, "predict_proba"):
        raise ModelError(f"El modelo {path.name} no tiene predict_proba")
    expected = getattr(model, "feature_names_in_", None)
    if expected is not None and list(expected) != FIELD_NAMES:
        missing = sorted(set(FIELD_NAMES) - set(expected))
        extra = sorted(set(expected) - set(FIELD_NAMES))
        raise ModelError(
            f"El modelo {path.name} espera otras columnas. Faltan: {missing or '-'}; sobran: {extra or '-'}"
        )


def _read_model_info(path):
    """Lee models/model_info.json (si existe) y lo mezcla con los valores por defecto."""
    settings = {**DEFAULT_SETTINGS, "version": path.stem}
    info_path = path.parent / "model_info.json"
    if not info_path.exists():
        return settings
    info = json.loads(info_path.read_text(encoding="utf-8"))
    levels = info.get("risk_levels", {})
    settings.update(
        version=str(info.get("version", settings["version"])),
        threshold=float(info.get("threshold", settings["threshold"])),
        medium_from=float(levels.get("medium_from", settings["medium_from"])),
        high_from=float(levels.get("high_from", settings["high_from"])),
    )
    return settings


def _load():
    model_path = os.environ.get("MODEL_PATH", "").strip()
    if model_path:
        path = Path(model_path)
        path = path if path.is_absolute() else ROOT / path
        if path.exists():
            model = joblib.load(path)  # Solo cargar .pkl de confianza: joblib puede ejecutar código.
            _check_model(model, path)
            log.info("Modelo cargado: %s", path)
            return model, _read_model_info(path)
        if _env_flag("REQUIRE_MODEL"):
            raise ModelError(f"MODEL_PATH apunta a {path}, pero ese archivo no existe")
        log.warning("MODEL_PATH apunta a %s, que no existe: se usa el modelo de PRUEBA", path)
    else:
        log.warning("MODEL_PATH no está definida: se usa el modelo de PRUEBA")
    return _train_demo_model(), dict(DEFAULT_SETTINGS)


# El modelo se guarda aquí la primera vez. El candado evita entrenarlo dos veces
# si llegan varias peticiones juntas justo al arrancar.
_lock = threading.Lock()
_loaded = None


def load_model():
    """Devuelve (modelo, ajustes). Carga el modelo solo la primera vez."""
    global _loaded
    if _loaded is None:
        with _lock:
            if _loaded is None:
                _loaded = _load()
    return _loaded


def reset():
    """Olvida el modelo cargado (lo usan las pruebas para cambiar MODEL_PATH)."""
    global _loaded
    with _lock:
        _loaded = None


def is_loaded():
    return _loaded is not None


def model_version():
    return load_model()[1]["version"]


def risk_level(probability, settings=DEFAULT_SETTINGS):
    if probability >= settings["high_from"]:
        return "high"
    if probability >= settings["medium_from"]:
        return "medium"
    return "low"


def predict_many(customers):
    """Predice una lista de clientes ya validados, en UNA sola llamada al modelo."""
    model, settings = load_model()
    if not customers:
        return []
    rows = pd.DataFrame(customers, columns=FIELD_NAMES)
    results = []
    for p in model.predict_proba(rows)[:, 1]:
        # Se redondea antes de clasificar para que el nivel coincida con el número que ve el usuario.
        probability = round(float(p), 2)
        results.append(
            {
                "churn": probability >= settings["threshold"],
                "probability": probability,
                "risk_level": risk_level(probability, settings),
                "model_version": settings["version"],
            }
        )
    return results


def predict_customer(customer):
    """Predice un cliente ya validado (ver schema.validate_customer)."""
    return predict_many([customer])[0]
