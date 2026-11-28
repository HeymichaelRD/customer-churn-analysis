"""Ingeniería determinista de variables compartida entre entrenamiento e inferencia."""

from __future__ import annotations

import pandas as pd


SERVICE_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]
SECURITY_SUPPORT_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
]
STREAMING_COLUMNS = ["StreamingTV", "StreamingMovies"]
ENGINEERED_FEATURES = ["SecuritySupportCount", "StreamingServicesCount"]


def build_model_features(data: pd.DataFrame) -> pd.DataFrame:
    """Sustituye seis indicadores de servicios de internet por dos conteos.

    Recibe las columnas de entrada que conserva el contrato del modelo y
    devuelve la tabla reducida que usa el clasificador. Un servicio cuenta
    como activo solo si su valor es ``Yes``; tanto ``No`` como
    ``No internet service`` cuentan como cero.
    Se conserva ``InternetService`` para distinguir a quienes no tienen
    internet de quienes sí tienen, pero no contrataron servicios adicionales.
    """
    missing = [column for column in SERVICE_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas para resumir servicios: {missing}")

    features = data.copy()
    for column in SERVICE_COLUMNS:
        features[column] = (features[column] == "Yes").astype("int8")

    features["SecuritySupportCount"] = features[SECURITY_SUPPORT_COLUMNS].sum(axis=1)
    features["StreamingServicesCount"] = features[STREAMING_COLUMNS].sum(axis=1)
    return features.drop(columns=SERVICE_COLUMNS)
