"""
Limpieza del dataset Telco Customer Churn.

Autor: Bryan Abreu
Fecha: 22 de noviembre de 2026
Equipo: Limpieza y EDA (rama cleaning-eda)

Qué hace este script:
    Paso 1. Carga el dataset original de data/raw/ (no lo modifica).
    Paso 2. Verifica que es la data oficial del proyecto: archivo, filas,
            columnas, valores permitidos y reglas de coherencia del
            contrato de la API (README, "Contratos entre equipos").
    Paso 3. Limpia TotalCharges: lo convierte a número y llena con 0 los
            11 valores vacíos (clientes con tenure 0, recién llegados).
    Paso 4. Verifica el resultado: mismas filas y columnas, sin nulos.
    Paso 5. Guarda el archivo limpio en data/processed/telco_churn_clean.csv.
    Paso 6. Guarda los datos para el dashboard en
            data/output/telco_churn_dashboard.csv: el archivo limpio más
            churn_flag (1 si se fue, 0 si se quedó) y tenure_group
            (antigüedad en rangos de 12 meses, los mismos del EDA).

Criterio: la limpieza solo toca TotalCharges. Las demás columnas mantienen
los mismos nombres y valores del original (SeniorCitizen en 0/1, Churn en
Yes/No, "No internet service", etc.), porque el contrato de la API y el
Pipeline del equipo de Modelos esperan las columnas originales.

Criterio del archivo del dashboard: las columnas extra solo van en
data/output/, para que Power BI muestre las mismas cifras que la web. La
columna segment (K-Means) la agrega el equipo de Modelos uniendo por
customerID, porque la segmentación no es nuestra.

Cómo ejecutarlo (desde la raíz del repo, con el .venv activo):
    python src/cleaning/clean_data.py
"""

from pathlib import Path

import pandas as pd

# Rutas a partir de la raíz del repo, para que funcione desde cualquier carpeta
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "telco_churn_clean.csv"
DASHBOARD_PATH = PROJECT_ROOT / "data" / "output" / "telco_churn_dashboard.csv"

# Mismos rangos de antigüedad que el EDA (notebooks/02_eda_bryan.ipynb)
TENURE_BINS = [-1, 12, 24, 48, 72]
TENURE_LABELS = ["0-12 meses", "13-24 meses", "25-48 meses", "49-72 meses"]

EXPECTED_ROWS = 7043

# Los 19 campos del contrato de la API, en el orden del dataset
API_FIELDS = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
    "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling",
    "PaymentMethod", "MonthlyCharges", "TotalCharges",
]
EXPECTED_COLUMNS = ["customerID"] + API_FIELDS + ["Churn"]

YES_NO = {"Yes", "No"}
INTERNET_EXTRAS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                   "TechSupport", "StreamingTV", "StreamingMovies"]
ALLOWED_VALUES = {
    "gender": {"Female", "Male"},
    "SeniorCitizen": {0, 1},
    "Partner": YES_NO,
    "Dependents": YES_NO,
    "PhoneService": YES_NO,
    "PaperlessBilling": YES_NO,
    "Churn": YES_NO,
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaymentMethod": {"Electronic check", "Mailed check",
                      "Bank transfer (automatic)", "Credit card (automatic)"},
    **{col: {"Yes", "No", "No internet service"} for col in INTERNET_EXTRAS},
}


def load_raw(path: Path) -> pd.DataFrame:
    """Paso 1: carga el dataset original."""
    print(f"Paso 1. Cargando {path.relative_to(PROJECT_ROOT)}")
    return pd.read_csv(path)


def validate_raw(df: pd.DataFrame) -> None:
    """Paso 2: comprueba que la data es la oficial del proyecto."""
    print("Paso 2. Verificando que la data coincide con el README y el contrato de la API")

    # Filas y columnas que indica el README
    assert len(df) == EXPECTED_ROWS, f"Se esperaban {EXPECTED_ROWS} filas y hay {len(df)}"
    assert list(df.columns) == EXPECTED_COLUMNS, "Las columnas no coinciden con las del contrato"
    assert not df["customerID"].duplicated().any(), "Hay customerID duplicados"

    # Valores permitidos de cada columna categórica
    for col, allowed in ALLOWED_VALUES.items():
        extra = set(df[col].unique()) - allowed
        assert not extra, f"{col} tiene valores fuera del contrato: {extra}"
    assert (df["tenure"] >= 0).all(), "Hay tenure negativo"
    assert (df["MonthlyCharges"] > 0).all(), "Hay MonthlyCharges en 0 o negativo"

    # Reglas de coherencia del contrato
    no_phone = df["PhoneService"] == "No"
    assert (df.loc[no_phone, "MultipleLines"] == "No phone service").all()
    assert (df.loc[~no_phone, "MultipleLines"] != "No phone service").all()
    no_internet = df["InternetService"] == "No"
    assert (df.loc[no_internet, INTERNET_EXTRAS] == "No internet service").all().all()
    assert (df.loc[~no_internet, INTERNET_EXTRAS] != "No internet service").all().all()
    assert not (no_phone & no_internet).any(), "Hay clientes sin teléfono ni internet"

    print("         OK: archivo, columnas, valores y reglas correctos")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Paso 3: convierte TotalCharges a número y llena los vacíos con 0."""
    print("Paso 3. Limpiando TotalCharges")
    clean_df = df.copy()

    total = pd.to_numeric(clean_df["TotalCharges"], errors="coerce")
    blank = total.isna()

    # Los vacíos solo pueden ser clientes nuevos (tenure 0); si no, algo cambió en la data
    assert (clean_df.loc[blank, "tenure"] == 0).all(), "Hay TotalCharges vacíos con tenure mayor que 0"

    # Clientes recién llegados: todavía no han pagado nada, su cargo total es 0
    clean_df["TotalCharges"] = total.fillna(0.0)
    print(f"         {blank.sum()} valores vacíos llenados con 0 (todos con tenure 0)")
    return clean_df


def validate_clean(raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> None:
    """Paso 4: comprueba que la limpieza no rompió nada."""
    print("Paso 4. Verificando el resultado")
    assert clean_df.shape == raw_df.shape, "Cambió el número de filas o columnas"
    assert list(clean_df.columns) == EXPECTED_COLUMNS, "Cambiaron las columnas"
    assert clean_df.isna().sum().sum() == 0, "Quedaron valores nulos"
    assert pd.api.types.is_float_dtype(clean_df["TotalCharges"]), "TotalCharges no es numérico"
    assert (clean_df["TotalCharges"] >= 0).all(), "Hay TotalCharges negativo"

    # Las demás columnas deben quedar exactamente igual que en el original
    untouched = [c for c in EXPECTED_COLUMNS if c != "TotalCharges"]
    assert clean_df[untouched].equals(raw_df[untouched]), "Se modificaron columnas que no debían cambiar"
    print("         OK: 7,043 filas, 21 columnas, sin nulos y el resto de columnas sin cambios")


def save(df: pd.DataFrame, path: Path) -> None:
    """Paso 5: guarda el archivo limpio."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Paso 5. Archivo guardado en {path.relative_to(PROJECT_ROOT)}")


def save_dashboard_data(clean_df: pd.DataFrame, path: Path) -> None:
    """Paso 6: guarda los datos para el dashboard de Power BI."""
    dashboard_df = clean_df.copy()
    dashboard_df["churn_flag"] = (dashboard_df["Churn"] == "Yes").astype(int)
    dashboard_df["tenure_group"] = pd.cut(dashboard_df["tenure"], bins=TENURE_BINS, labels=TENURE_LABELS)

    # La tasa de churn debe ser la misma del EDA
    churn_rate = round(dashboard_df["churn_flag"].mean() * 100, 1)
    assert dashboard_df.isna().sum().sum() == 0, "Quedaron valores nulos en los datos del dashboard"
    assert churn_rate == 26.5, f"La tasa de churn es {churn_rate}% y el EDA dice 26.5%"

    path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_df.to_csv(path, index=False)
    print(f"Paso 6. Datos del dashboard guardados en {path.relative_to(PROJECT_ROOT)} (churn de {churn_rate}%)")


def main() -> None:
    raw_df = load_raw(RAW_PATH)
    validate_raw(raw_df)
    clean_df = clean(raw_df)
    validate_clean(raw_df, clean_df)
    save(clean_df, PROCESSED_PATH)
    save_dashboard_data(clean_df, DASHBOARD_PATH)
    print("Listo. Limpieza terminada.")


if __name__ == "__main__":
    main()
