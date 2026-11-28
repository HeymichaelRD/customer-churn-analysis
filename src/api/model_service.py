"""Carga los modelos y calcula el riesgo de abandono y el segmento de uno o varios clientes.

Modelo de churn:
- Si MODEL_PATH (variable del .env) apunta a un archivo que existe, usa ese modelo: el del equipo
  de Modelos. El umbral para responder churn = true sale de MODEL_INFO_PATH
  (por defecto models/churn_model_info.json). Sin ese archivo la API no arranca: con el umbral
  equivocado, el modelo marcaría a los clientes que no son.
- Si MODEL_PATH no está definida, o apunta a un archivo que no existe, usa un MODELO DE PRUEBA
  entrenado aquí mismo con data/raw (y lo avisa en el log). Con REQUIRE_MODEL=1 en el .env,
  eso es un error y la API no arranca: útil para la demo final.

Segmentación (K-Means):
- Usa SEGMENTS_MODEL_PATH y SEGMENTS_INFO_PATH (por defecto, los archivos de models/).
  Si el modelo no existe, el segmento sale como null (o la API no arranca, con REQUIRE_MODEL=1).
- Al K-Means solo se le pasan las columnas de "columns" en segments_info.json
  (tenure, MonthlyCharges, Contract e InternetService): son las únicas que usa.

Los modelos se cargan una sola vez (al arrancar la API, ver app.py) y se reutilizan.
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

DEFAULT_MODEL_INFO = "models/churn_model_info.json"
DEFAULT_SEGMENTS_MODEL = "models/telco_customer_segments.joblib"
DEFAULT_SEGMENTS_INFO = "models/segments_info.json"

# Umbral del modelo de prueba. El del modelo real sale de churn_model_info.json.
DEMO_THRESHOLD = 0.50
# Niveles de riesgo provisionales (ver docs/plan-api-web.md). Se ajustan con el equipo de Modelos.
MEDIUM_FROM = 0.30
HIGH_FROM = 0.60

NUMERIC = ["tenure", "MonthlyCharges", "SecuritySupportCount", "StreamingServicesCount"]
CATEGORICAL = [name for name in FIELD_NAMES if name not in NUMERIC]

# Servicios del dataset que suma cada conteo (igual que la página web antes de enviar).
COUNTED_SERVICES = {
    "SecuritySupportCount": ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport"],
    "StreamingServicesCount": ["StreamingTV", "StreamingMovies"],
}


class ModelError(Exception):
    """Un modelo no se pudo cargar o no es compatible con el contrato."""


def _env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def _env_path(name, default=None):
    """Ruta de una variable del .env. Las rutas relativas son desde la raíz del repo."""
    value = os.environ.get(name, "").strip() or default
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _read_json(path, what):
    if not path.exists():
        raise ModelError(f"No se encontró {what}: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ModelError(f"{what} no es un JSON válido ({path}): {error}") from error


def _load_joblib(path):
    # Solo cargar archivos de confianza: joblib puede ejecutar código al cargarlos.
    try:
        return joblib.load(path)
    except ImportError as error:
        raise ModelError(f"No se pudo cargar {path.name}: falta el módulo {error.name}") from error


def _check_columns(model, path):
    """Falla al cargar (y no en la primera predicción) si el modelo espera otras columnas."""
    expected = getattr(model, "feature_names_in_", None)
    if expected is not None and list(expected) != FIELD_NAMES:
        missing = sorted(set(FIELD_NAMES) - set(expected))
        extra = sorted(set(expected) - set(FIELD_NAMES))
        raise ModelError(
            f"El modelo {path.name} espera otras columnas. Faltan: {missing or '-'}; sobran: {extra or '-'}"
        )


# --- Modelo de churn -------------------------------------------------------


def add_service_counts(df):
    """Agrega a una tabla del dataset los dos conteos del contrato ("Yes" cuenta 1)."""
    for name, services in COUNTED_SERVICES.items():
        df[name] = (df[services] == "Yes").sum(axis=1)
    return df


def _train_demo_model():
    # Modelo de prueba: regresión logística con los mismos 12 campos del contrato.
    df = add_service_counts(pd.read_csv(RAW_DATA))
    X, y = df[FIELD_NAMES], (df["Churn"] == "Yes").astype(int)

    preprocess = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("model", LogisticRegression(max_iter=1000))]).fit(X, y)


def _read_threshold(info_path):
    """Umbral de churn_model_info.json. Revisa que el modelo use los 12 campos del contrato."""
    info = _read_json(info_path, "la información del modelo de churn")

    threshold = info.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        raise ModelError(f'{info_path.name} debe tener un "threshold" entre 0 y 1')

    columns = info.get("input_columns")
    if columns is not None and list(columns) != FIELD_NAMES:
        raise ModelError(f"{info_path.name} indica otras columnas de entrada que las del contrato")
    return float(threshold)


def _load_churn_model():
    """Devuelve (modelo, versión, umbral)."""
    path = _env_path("MODEL_PATH")
    if path is None:
        problem = "MODEL_PATH no está definida"
    elif not path.exists():
        problem = f"MODEL_PATH apunta a {path}, pero ese archivo no existe"
    else:
        model = _load_joblib(path)
        if not hasattr(model, "predict_proba"):
            raise ModelError(f"El modelo {path.name} no tiene predict_proba")
        _check_columns(model, path)
        threshold = _read_threshold(_env_path("MODEL_INFO_PATH", DEFAULT_MODEL_INFO))
        log.info("Modelo de churn cargado: %s (umbral %.3f)", path, threshold)
        return model, path.stem, threshold

    if _env_flag("REQUIRE_MODEL"):
        raise ModelError(problem)
    log.warning("%s: se usa el modelo de PRUEBA", problem)
    return _train_demo_model(), DEMO_VERSION, DEMO_THRESHOLD


# --- Segmentación (K-Means) -----------------------------------------------


def _n_clusters(model):
    estimator = model.steps[-1][1] if hasattr(model, "steps") else model
    return getattr(estimator, "n_clusters", None)


def _segment_columns(info, model, path):
    """Columnas que usa el K-Means: "columns" de segments_info.json.

    Deben ser campos del contrato (si no, la API no las recibe) y columnas con las que se
    entrenó el modelo.
    """
    columns = info.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ModelError('segments_info.json debe tener "columns": las columnas que usa el K-Means')
    missing = [c for c in columns if c not in FIELD_NAMES]
    if missing:
        raise ModelError(f"El K-Means usa columnas que no están en el contrato de la API: {missing}")
    trained = getattr(model, "feature_names_in_", None)
    if trained is not None and not set(columns) <= set(trained):
        raise ModelError(f"El modelo {path.name} no se entrenó con las columnas {columns}")
    return list(columns)


def _load_segments():
    """Devuelve (modelo, {id: segmento}, columnas) o (None, {}, []) si no hay modelo de segmentación."""
    path = _env_path("SEGMENTS_MODEL_PATH", DEFAULT_SEGMENTS_MODEL)
    if not path.exists():
        if _env_flag("REQUIRE_MODEL"):
            raise ModelError(f"No se encontró el modelo de segmentación: {path}")
        log.warning("No se encontró el modelo de segmentación (%s): el segmento será null", path)
        return None, {}, []

    model = _load_joblib(path)
    info = _read_json(_env_path("SEGMENTS_INFO_PATH", DEFAULT_SEGMENTS_INFO), "la información de los segmentos")
    columns = _segment_columns(info, model, path)
    segments = {
        int(s["id"]): {"id": int(s["id"]), "name": s["name"], "description": s.get("description", "")}
        for s in info.get("segments", [])
    }

    # Cada ID que puede devolver el modelo (0 a k-1) debe tener su nombre en segments_info.json.
    # Si alguien vuelve a entrenar uno sin actualizar el otro, es mejor que la API no arranque
    # a que muestre el nombre de otro segmento.
    k = _n_clusters(model)
    if k is not None and sorted(segments) != list(range(k)):
        raise ModelError(
            f"segments_info.json no coincide con el modelo: el modelo tiene {k} segmentos "
            f"(IDs 0 a {k - 1}) y el JSON trae los IDs {sorted(segments)}"
        )
    log.info("Modelo de segmentación cargado: %s (%d segmentos, columnas %s)", path, len(segments), columns)
    return model, segments, columns


# --- Carga única ----------------------------------------------------------

# Los modelos se guardan aquí la primera vez. El candado evita cargarlos dos veces
# si llegan varias peticiones juntas justo al arrancar.
_lock = threading.Lock()
_loaded = None


def load_models():
    """Carga los modelos solo la primera vez y devuelve un diccionario con todo lo cargado."""
    global _loaded
    if _loaded is None:
        with _lock:
            if _loaded is None:
                model, version, threshold = _load_churn_model()
                segments_model, segments, segment_columns = _load_segments()
                _loaded = {
                    "model": model,
                    "version": version,
                    "threshold": threshold,
                    "segments_model": segments_model,
                    "segments": segments,
                    "segment_columns": segment_columns,
                }
    return _loaded


def reset():
    """Olvida los modelos cargados (lo usan las pruebas para cambiar las variables del .env)."""
    global _loaded
    with _lock:
        _loaded = None


def model_version():
    return load_models()["version"]


def risk_level(probability):
    if probability >= HIGH_FROM:
        return "high"
    if probability >= MEDIUM_FROM:
        return "medium"
    return "low"


def predict_many(customers):
    """Predice una lista de clientes ya validados, con UNA sola llamada a cada modelo."""
    state = load_models()
    if not customers:
        return []
    rows = pd.DataFrame(customers, columns=FIELD_NAMES)
    probabilities = state["model"].predict_proba(rows)[:, 1]
    if state["segments_model"] is not None:
        segment_ids = state["segments_model"].predict(rows[state["segment_columns"]])
    else:
        segment_ids = [None] * len(rows)

    results = []
    for p, segment_id in zip(probabilities, segment_ids):
        # Se redondea antes de clasificar para que el resultado coincida con el número que ve el
        # usuario (si no, 0.597 se mostraría como 0.60 pero con riesgo "medium").
        probability = round(float(p), 2)
        results.append(
            {
                "churn": probability >= state["threshold"],
                "probability": probability,
                "risk_level": risk_level(probability),
                "segment": None if segment_id is None else state["segments"][int(segment_id)],
                "model_version": state["version"],
            }
        )
    return results


def predict_customer(customer):
    """Predice un cliente ya validado (ver schema.validate_customer)."""
    return predict_many([customer])[0]
