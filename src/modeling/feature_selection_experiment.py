"""Evalúa opciones para reducir variables en los modelos de churn de Telco.

Este experimento conserva intacto el dataset limpio. Compara conjuntos de
variables candidatos con la misma partición y probabilidades OOF de train.
La partición de prueba existente no se usa para ordenar las opciones.
"""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.modeling.feature_engineering import build_model_features


RANDOM_STATE = 42
TEST_SIZE = 0.20
N_SPLITS = 5
THRESHOLDS = np.linspace(0.05, 0.80, 151)
SIMILAR_F1_TOLERANCE = 0.005

DATA_PATH = ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_PATH = ROOT / "data" / "output" / "feature_selection_cv.csv"
FINALIST_TEST_PATH = ROOT / "data" / "output" / "feature_selection_finalist_test.json"

SERVICE_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]
PHONE_COLUMNS = ["PhoneService", "MultipleLines"]
NO_SERVICE_MAP = {
    "No internet service": "No",
    "No phone service": "No",
}


def build_candidates(X: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Devuelve variantes de variables sin modificar el DataFrame original."""
    candidates: dict[str, pd.DataFrame] = {"Base completa": X.copy()}
    candidates["Sin PhoneService y MultipleLines"] = X.drop(columns=PHONE_COLUMNS)
    candidates["Sin gender"] = X.drop(columns=["gender"])
    candidates["Sin TotalCharges"] = X.drop(columns=["TotalCharges"])
    candidates["Reducida: sin gender, teléfono ni TotalCharges"] = X.drop(
        columns=["gender", *PHONE_COLUMNS, "TotalCharges"]
    )

    recoded = X.copy()
    service_and_phone = [*SERVICE_COLUMNS, "MultipleLines"]
    for column in service_and_phone:
        recoded[column] = recoded[column].replace(NO_SERVICE_MAP)
    candidates["Recodificada: servicios no disponibles como No"] = recoded

    bundled = build_model_features(X)
    candidates["Servicios agrupados en dos conteos"] = bundled

    compact = bundled.drop(columns=["gender", *PHONE_COLUMNS, "TotalCharges"])
    candidates["Compacta + servicios agrupados"] = compact
    return candidates


def make_pipeline(X: pd.DataFrame, estimator) -> Pipeline:
    numeric = X.select_dtypes(include=["number"]).columns.tolist()
    categorical = X.select_dtypes(exclude=["number"]).columns.tolist()

    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, numeric),
            ("categorical", categorical_pipeline, categorical),
        ]
    )
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def make_estimators() -> dict:
    return {
        "Regresión logística": LogisticRegression(
            max_iter=2000, random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
    }


def choose_threshold(y_true: pd.Series, probabilities: np.ndarray) -> float:
    """Maximiza F1 OOF; si hay empate exacto, prefiere mayor recall."""
    scored = []
    for threshold in THRESHOLDS:
        predictions = (probabilities >= threshold).astype(int)
        scored.append(
            (
                f1_score(y_true, predictions, zero_division=0),
                recall_score(y_true, predictions, zero_division=0),
                float(threshold),
            )
        )
    return max(scored)[2]


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el CSV limpio: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    if "customerID" not in df or "Churn" not in df:
        raise ValueError("El CSV debe incluir customerID y Churn.")
    if df["customerID"].duplicated().any():
        raise ValueError("customerID tiene duplicados.")

    X = df.drop(columns=["customerID", "Churn"])
    y = (df["Churn"] == "Yes").astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    candidates = build_candidates(X)
    cv = StratifiedKFold(
        n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
    )
    rows = []
    estimators = make_estimators()

    for candidate_name, candidate_X in candidates.items():
        candidate_train = candidate_X.loc[X_train.index]
        for model_name, estimator in estimators.items():
            pipeline = make_pipeline(candidate_train, estimator)
            oof_probabilities = cross_val_predict(
                pipeline,
                candidate_train,
                y_train,
                cv=cv,
                method="predict_proba",
                n_jobs=1,
            )[:, 1]
            threshold = choose_threshold(y_train, oof_probabilities)
            oof_predictions = (oof_probabilities >= threshold).astype(int)
            rows.append(
                {
                    "variant": candidate_name,
                    "model": model_name,
                    "input_features": candidate_X.shape[1],
                    "threshold_oof": threshold,
                    "precision_oof": precision_score(
                        y_train, oof_predictions, zero_division=0
                    ),
                    "recall_oof": recall_score(
                        y_train, oof_predictions, zero_division=0
                    ),
                    "f1_oof": f1_score(
                        y_train, oof_predictions, zero_division=0
                    ),
                }
            )
            print(
                f"{candidate_name} | {model_name} | "
                f"F1={rows[-1]['f1_oof']:.3f} "
                f"Recall={rows[-1]['recall_oof']:.3f} "
                f"umbral={threshold:.3f}",
                flush=True,
            )

    results = pd.DataFrame(rows).sort_values(
        ["f1_oof", "recall_oof", "input_features"],
        ascending=[False, False, True],
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    best_f1 = results["f1_oof"].max()
    similar = results[results["f1_oof"] >= best_f1 - SIMILAR_F1_TOLERANCE]
    preferred = similar.sort_values(
        ["recall_oof", "input_features", "f1_oof"],
        ascending=[False, True, False],
    ).iloc[0]

    print("\nResultados OOF ordenados por F1 y recall:")
    print(results.round(3).to_string(index=False))
    print(
        "\nCandidata sugerida (entre las que quedan a <= "
        f"{SIMILAR_F1_TOLERANCE:.3f} del F1 máximo):\n"
        f"{preferred['variant']} + {preferred['model']} | "
        f"F1={preferred['f1_oof']:.3f}, "
        f"Recall={preferred['recall_oof']:.3f}, "
        f"variables={int(preferred['input_features'])}"
    )
    print(f"\nTabla guardada en: {OUTPUT_PATH}")

    # Las variables, el modelo y el umbral se eligen solo con OOF de train.
    # La partición de reserva se usa una vez para evaluar la opción elegida.
    winner_name = str(preferred["variant"])
    winner_model = str(preferred["model"])
    winner_threshold = float(preferred["threshold_oof"])
    winner_train = candidates[winner_name].loc[X_train.index]
    winner_test = candidates[winner_name].loc[X_test.index]
    final_pipeline = make_pipeline(winner_train, make_estimators()[winner_model])
    final_pipeline.fit(winner_train, y_train)
    test_probabilities = final_pipeline.predict_proba(winner_test)[:, 1]
    test_predictions = (test_probabilities >= winner_threshold).astype(int)
    test_results = {
        "variant": winner_name,
        "model": winner_model,
        "input_features": int(preferred["input_features"]),
        "threshold_selected_on_train_oof": winner_threshold,
        "test_precision_yes": precision_score(
            y_test, test_predictions, zero_division=0
        ),
        "test_recall_yes": recall_score(y_test, test_predictions, zero_division=0),
        "test_f1_yes": f1_score(y_test, test_predictions, zero_division=0),
        "test_confusion_matrix_labels_0_1": confusion_matrix(
            y_test, test_predictions, labels=[0, 1]
        ).tolist(),
        "note": "Threshold and candidate were selected without using the test split.",
    }
    baseline_threshold = float(
        results.loc[
            (results["variant"] == "Base completa")
            & (results["model"] == winner_model),
            "threshold_oof",
        ].iloc[0]
    )
    baseline_train = candidates["Base completa"].loc[X_train.index]
    baseline_test = candidates["Base completa"].loc[X_test.index]
    baseline_pipeline = make_pipeline(
        baseline_train, make_estimators()[winner_model]
    )
    baseline_pipeline.fit(baseline_train, y_train)
    baseline_predictions = (
        baseline_pipeline.predict_proba(baseline_test)[:, 1] >= baseline_threshold
    ).astype(int)
    baseline_results = {
        "variant": "Base completa",
        "model": winner_model,
        "input_features": int(baseline_train.shape[1]),
        "threshold_selected_on_train_oof": baseline_threshold,
        "test_precision_yes": precision_score(
            y_test, baseline_predictions, zero_division=0
        ),
        "test_recall_yes": recall_score(
            y_test, baseline_predictions, zero_division=0
        ),
        "test_f1_yes": f1_score(y_test, baseline_predictions, zero_division=0),
        "test_confusion_matrix_labels_0_1": confusion_matrix(
            y_test, baseline_predictions, labels=[0, 1]
        ).tolist(),
    }
    test_results["baseline_reference"] = baseline_results
    FINALIST_TEST_PATH.write_text(json.dumps(test_results, indent=2) + "\n")
    print("\nComparación final en test reservado (candidata frente a base completa):")
    print(json.dumps(test_results, indent=2, ensure_ascii=False))
    print(f"Resumen de test guardado en: {FINALIST_TEST_PATH}")


if __name__ == "__main__":
    main()
