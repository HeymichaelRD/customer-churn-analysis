"""Compara una reducción adicional de variables frente a la base actual de 15."""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, precision_score, recall_score
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


DATA_PATH = ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_DIR = ROOT / "data" / "output"
SCREENING_PATH = OUTPUT_DIR / "feature_reduction_screening.csv"
PATH_PATH = OUTPUT_DIR / "feature_reduction_path.csv"
REPEATED_PATH = OUTPUT_DIR / "feature_reduction_repeated_holdout.csv"
HOLDOUT_PATH = OUTPUT_DIR / "feature_reduction_holdout.json"

RANDOM_STATE = 42
FINAL_HOLDOUT_STATE = 47
REPEATED_STATES = [42, 43, 44, 45, 46]
N_SPLITS = 5
F1_TOLERANCE = 0.005
THRESHOLDS = np.linspace(0.05, 0.80, 151)
BASE_FEATURES = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "SecuritySupportCount",
    "StreamingServicesCount",
]


def make_pipeline(features: pd.DataFrame) -> Pipeline:
    """Crea el preprocesamiento y Random Forest para un conjunto de variables."""
    numeric = features.select_dtypes(include=["number"]).columns.tolist()
    categorical = features.select_dtypes(exclude=["number"]).columns.tolist()
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=400,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
        ]
    )


def choose_threshold(y_true: pd.Series, probabilities: np.ndarray) -> float:
    """Elige el umbral que maximiza F1 en predicciones OOF."""
    scored = []
    for threshold in THRESHOLDS:
        predictions = probabilities >= threshold
        scored.append(
            (
                f1_score(y_true, predictions, zero_division=0),
                recall_score(y_true, predictions, zero_division=0),
                float(threshold),
            )
        )
    return max(scored)[2]


def evaluate_oof(
    features: pd.DataFrame,
    target: pd.Series,
    cv: StratifiedKFold,
) -> dict:
    """Evalúa una candidata con predicciones OOF y ajusta su umbral."""
    probabilities = cross_val_predict(
        make_pipeline(features),
        features,
        target,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    threshold = choose_threshold(target, probabilities)
    predictions = probabilities >= threshold
    return {
        "threshold_oof": threshold,
        "precision_oof": precision_score(target, predictions, zero_division=0),
        "recall_oof": recall_score(target, predictions, zero_division=0),
        "f1_oof": f1_score(target, predictions, zero_division=0),
    }


def build_candidates(features: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Prepara reducciones individuales y combinadas sin alterar la base."""
    candidates = {"Base actual (15)": features.copy()}
    for column in BASE_FEATURES:
        candidates[f"Sin {column}"] = features.drop(columns=[column])

    removals = {
        "Sin gender y SeniorCitizen": ["gender", "SeniorCitizen"],
        "Sin Partner y Dependents": ["Partner", "Dependents"],
        "Sin PhoneService y MultipleLines": ["PhoneService", "MultipleLines"],
        "Sin teléfono y TotalCharges": [
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
        ],
        "Sin gender, teléfono y TotalCharges": [
            "gender",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
        ],
        "Sin demografía ni teléfono": [
            "gender",
            "SeniorCitizen",
            "Partner",
            "Dependents",
            "PhoneService",
            "MultipleLines",
        ],
        "Sin MonthlyCharges ni TotalCharges": ["MonthlyCharges", "TotalCharges"],
        "Sin ambos conteos de servicios": [
            "SecuritySupportCount",
            "StreamingServicesCount",
        ],
        "Sin StreamingServicesCount": ["StreamingServicesCount"],
        "Sin SecuritySupportCount": ["SecuritySupportCount"],
        "Compacta: sin demografía, teléfono y TotalCharges": [
            "gender",
            "SeniorCitizen",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
        ],
        "Compacta: sin demografía, teléfono, TotalCharges y familia": [
            "gender",
            "SeniorCitizen",
            "Partner",
            "Dependents",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
        ],
        "Compacta: sin PaperlessBilling adicional": [
            "gender",
            "SeniorCitizen",
            "Partner",
            "Dependents",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
            "PaperlessBilling",
        ],
        "Compacta: sin PaymentMethod adicional": [
            "gender",
            "SeniorCitizen",
            "Partner",
            "Dependents",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
            "PaperlessBilling",
            "PaymentMethod",
        ],
        "Compacta: sin StreamingServicesCount adicional": [
            "gender",
            "SeniorCitizen",
            "Partner",
            "Dependents",
            "PhoneService",
            "MultipleLines",
            "TotalCharges",
            "PaperlessBilling",
            "PaymentMethod",
            "StreamingServicesCount",
        ],
    }
    for name, columns in removals.items():
        candidates[name] = features.drop(columns=columns)
    return candidates


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el CSV limpio: {DATA_PATH}")

    data = pd.read_csv(DATA_PATH)
    raw_features = data.drop(columns=["customerID", "Churn"])
    features = build_model_features(raw_features)
    target = (data["Churn"] == "Yes").astype(int)
    X_train, _, y_train, _ = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=target,
    )
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    candidates = build_candidates(X_train)

    screening_rows = []
    for name, candidate in candidates.items():
        scores = evaluate_oof(candidate, y_train, cv)
        screening_rows.append(
            {
                "variant": name,
                "n_features": candidate.shape[1],
                **scores,
            }
        )
        print(
            f"{name}: {candidate.shape[1]} variables; "
            f"F1={scores['f1_oof']:.3f}; recall={scores['recall_oof']:.3f}",
            flush=True,
        )

    screening = pd.DataFrame(screening_rows).sort_values(
        ["f1_oof", "recall_oof", "n_features"],
        ascending=[False, False, True],
    )
    screening.to_csv(SCREENING_PATH, index=False)
    best_f1 = float(screening["f1_oof"].max())
    eligible = screening[screening["f1_oof"] >= best_f1 - F1_TOLERANCE]
    selected_name = str(
        eligible.sort_values(
            ["recall_oof", "n_features", "f1_oof"],
            ascending=[False, True, False],
        ).iloc[0]["variant"]
    )
    selected = candidates[selected_name]

    # Prueba eliminaciones adicionales hasta que ninguna mejore recall dentro
    # del margen de F1 establecido durante la selección inicial.
    path_rows = [
        {
            "step": 0,
            "removed_feature": "",
            "n_features": selected.shape[1],
            "features": ", ".join(selected.columns),
            **evaluate_oof(selected, y_train, cv),
        }
    ]
    while selected.shape[1] > 1:
        current = path_rows[-1]
        alternatives = []
        for column in selected.columns:
            candidate = selected.drop(columns=[column])
            score = evaluate_oof(candidate, y_train, cv)
            alternatives.append((column, candidate, score))
        eligible_drops = [
            item
            for item in alternatives
            if item[2]["f1_oof"] >= best_f1 - F1_TOLERANCE
            and item[2]["recall_oof"] > current["recall_oof"]
        ]
        if not eligible_drops:
            break
        removed, selected, score = max(
            eligible_drops,
            key=lambda item: (
                item[2]["recall_oof"],
                -item[1].shape[1],
                item[2]["f1_oof"],
            ),
        )
        path_rows.append(
            {
                "step": len(path_rows),
                "removed_feature": removed,
                "n_features": selected.shape[1],
                "features": ", ".join(selected.columns),
                **score,
            }
        )

    selected_columns = selected.columns.tolist()
    selected_name = "Reducción elegida"
    pd.DataFrame(path_rows).to_csv(PATH_PATH, index=False)

    # Compara la base y la reducción con cinco particiones estratificadas.
    variants = {
        "Base actual (15)": BASE_FEATURES,
        selected_name: selected_columns,
    }
    repeated_rows = []
    for seed in REPEATED_STATES:
        train_X, test_X, train_y, test_y = train_test_split(
            features,
            target,
            test_size=0.20,
            random_state=seed,
            stratify=target,
        )
        repeated_cv = StratifiedKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=seed
        )
        for name, columns in variants.items():
            train_features = train_X[columns]
            test_features = test_X[columns]
            scores = evaluate_oof(train_features, train_y, repeated_cv)
            model = make_pipeline(train_features).fit(train_features, train_y)
            predictions = (
                model.predict_proba(test_features)[:, 1]
                >= scores["threshold_oof"]
            )
            repeated_rows.append(
                {
                    "random_state": seed,
                    "variant": name,
                    "n_features": len(columns),
                    "threshold_oof": scores["threshold_oof"],
                    "precision_yes": precision_score(
                        test_y, predictions, zero_division=0
                    ),
                    "recall_yes": recall_score(
                        test_y, predictions, zero_division=0
                    ),
                    "f1_yes": f1_score(test_y, predictions, zero_division=0),
                }
            )
    repeated = pd.DataFrame(repeated_rows)
    repeated.to_csv(REPEATED_PATH, index=False)

    # Holdout final reservado; usa la mediana de los umbrales anteriores.
    train_X, test_X, train_y, test_y = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=FINAL_HOLDOUT_STATE,
        stratify=target,
    )
    holdout_rows = []
    for name, columns in variants.items():
        historical_thresholds = repeated.loc[
            repeated["variant"] == name, "threshold_oof"
        ]
        threshold = float(historical_thresholds.median())
        train_features = train_X[columns]
        test_features = test_X[columns]
        model = make_pipeline(train_features).fit(train_features, train_y)
        predictions = (
            model.predict_proba(test_features)[:, 1] >= threshold
        )
        holdout_rows.append(
            {
                "variant": name,
                "n_features": len(columns),
                "threshold": threshold,
                "precision_yes": precision_score(
                    test_y, predictions, zero_division=0
                ),
                "recall_yes": recall_score(test_y, predictions, zero_division=0),
                "f1_yes": f1_score(test_y, predictions, zero_division=0),
            }
        )

    summary = repeated.groupby("variant")[
        ["precision_yes", "recall_yes", "f1_yes"]
    ].agg(["mean", "std"])
    report = {
        "selected_variant": selected_name,
        "selected_features": selected_columns,
        "screening_best_f1": best_f1,
        "f1_tolerance": F1_TOLERANCE,
        "holdout_random_state": FINAL_HOLDOUT_STATE,
        "holdout_comparison": holdout_rows,
        "repeated_holdout_summary": json.loads(summary.to_json(orient="index")),
        "note": (
            "El conjunto de prueba final no se usó para seleccionar variables "
            "ni ajustar umbrales. La búsqueda inicial usa OOF del 80% de train."
        ),
    }
    HOLDOUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"\nReducción elegida: {len(selected_columns)} variables")
    print(", ".join(selected_columns))
    print("\nResumen de divisiones repetidas:")
    print(summary.round(3).to_string())
    print("\nEvaluación del holdout independiente:")
    print(json.dumps(holdout_rows, ensure_ascii=False, indent=2))
    print(f"\nSalidas guardadas en {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
