"""Compara dos clasificadores en varias particiones estratificadas.

Usa el resumen elegido de servicios y ajusta el umbral de cada clasificador
con predicciones OOF del conjunto de entrenamiento de cada partición.
"""

from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.modeling.feature_engineering import build_model_features


DATA_PATH = ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_PATH = ROOT / "data" / "output" / "final_classifier_repeated_holdout.csv"
FINAL_HOLDOUT_PATH = ROOT / "data" / "output" / "final_classifier_holdout.json"
RANDOM_STATES = [42, 43, 44, 45, 46]
FINAL_HOLDOUT_STATE = 47
THRESHOLDS = np.linspace(0.05, 0.80, 151)


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    engineered = build_model_features(X)
    numeric = engineered.select_dtypes(include=["number"]).columns.tolist()
    categorical = engineered.select_dtypes(exclude=["number"]).columns.tolist()
    return ColumnTransformer(
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


def classifiers() -> dict:
    return {
        "Regresión logística": LogisticRegression(
            max_iter=2000, random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=1,
        ),
    }


def main() -> None:
    data = pd.read_csv(DATA_PATH)
    X = data.drop(columns=["customerID", "Churn"])
    y = (data["Churn"] == "Yes").astype(int)
    rows = []

    for seed in RANDOM_STATES:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=seed, stratify=y
        )
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        preprocessor = build_preprocessor(X_train)

        for model_name, estimator in classifiers().items():
            pipeline = Pipeline(
                [
                    (
                        "feature_engineering",
                        FunctionTransformer(build_model_features, validate=False),
                    ),
                    ("preprocess", preprocessor),
                    ("model", estimator),
                ]
            )
            oof_probability = cross_val_predict(
                pipeline,
                X_train,
                y_train,
                cv=cv,
                method="predict_proba",
                n_jobs=1,
            )[:, 1]
            threshold = max(
                THRESHOLDS,
                key=lambda value: f1_score(
                    y_train, oof_probability >= value, zero_division=0
                ),
            )
            pipeline.fit(X_train, y_train)
            predictions = (
                pipeline.predict_proba(X_test)[:, 1] >= threshold
            ).astype(int)
            matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
            rows.append(
                {
                    "random_state": seed,
                    "model": model_name,
                    "threshold_oof": float(threshold),
                    "precision_yes": precision_score(
                        y_test, predictions, zero_division=0
                    ),
                    "recall_yes": recall_score(
                        y_test, predictions, zero_division=0
                    ),
                    "f1_yes": f1_score(y_test, predictions, zero_division=0),
                    "tn": int(matrix[0, 0]),
                    "fp": int(matrix[0, 1]),
                    "fn": int(matrix[1, 0]),
                    "tp": int(matrix[1, 1]),
                }
            )
            row = rows[-1]
            print(
                f"seed={seed} | {model_name} | "
                f"F1={row['f1_yes']:.3f} Recall={row['recall_yes']:.3f} "
                f"Precision={row['precision_yes']:.3f} "
                f"umbral={threshold:.3f}",
                flush=True,
            )

    results = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)
    summary = results.groupby("model")[
        ["precision_yes", "recall_yes", "f1_yes"]
    ].agg(["mean", "std"])
    print("\nPromedio y desviación estándar en las cinco divisiones:")
    print(summary.round(3).to_string())
    print(f"\nDetalle guardado en: {OUTPUT_PATH}")

    means = results.groupby("model")[["precision_yes", "recall_yes", "f1_yes"]].mean()
    best_f1 = means["f1_yes"].max()
    near_tie = means[means["f1_yes"] >= best_f1 - 0.005]
    selected_model = near_tie.sort_values(
        ["recall_yes", "f1_yes"], ascending=False
    ).index[0]
    selected_threshold = float(
        results.loc[results["model"] == selected_model, "threshold_oof"].median()
    )

    # Esta partición final no se usa para elegir el clasificador ni ajustar el umbral.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=FINAL_HOLDOUT_STATE,
        stratify=y,
    )
    pipeline = Pipeline(
        [
            (
                "feature_engineering",
                FunctionTransformer(build_model_features, validate=False),
            ),
            ("preprocess", build_preprocessor(X_train)),
            ("model", classifiers()[selected_model]),
        ]
    )
    pipeline.fit(X_train, y_train)
    predictions = (
        pipeline.predict_proba(X_test)[:, 1] >= selected_threshold
    ).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    final_report = {
        "model": selected_model,
        "variant": "Servicios agrupados en dos conteos",
        "threshold": selected_threshold,
        "threshold_source": "Median of OOF-tuned thresholds in the five model-selection splits.",
        "random_state": FINAL_HOLDOUT_STATE,
        "precision_yes": precision_score(y_test, predictions, zero_division=0),
        "recall_yes": recall_score(y_test, predictions, zero_division=0),
        "f1_yes": f1_score(y_test, predictions, zero_division=0),
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "note": "This final split was not used to select the classifier or threshold.",
    }
    FINAL_HOLDOUT_PATH.write_text(json.dumps(final_report, indent=2) + "\n")
    print("\nModelo seleccionado por F1 medio y recall en caso de empate cercano:")
    print(selected_model)
    print(f"Umbral robusto (mediana OOF): {selected_threshold:.3f}")
    print("Evaluación en holdout final separado:")
    print(json.dumps(final_report, indent=2, ensure_ascii=False))
    print(f"Resumen guardado en: {FINAL_HOLDOUT_PATH}")


if __name__ == "__main__":
    main()
