"""Compara variables candidatas y modelos para segmentar clientes Telco."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.modeling.feature_engineering import build_model_features

DATA_PATH = ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_PATH = ROOT / "data" / "output" / "clustering_model_comparison.csv"
FEATURE_OUTPUT_PATH = ROOT / "data" / "output" / "clustering_feature_comparison.csv"

RANDOM_STATE = 42
K_VALUES = range(2, 9)
SILHOUETTE_SAMPLE_SIZE = 2000
BASE_CLUSTER_FEATURES = ["tenure", "MonthlyCharges", "Contract"]
CLUSTER_FEATURES = [*BASE_CLUSTER_FEATURES, "InternetService"]
K_FEATURE_SCREEN = 4


def make_preprocessor(data: pd.DataFrame, columns: list[str]) -> ColumnTransformer:
    """Escala variables numéricas y codifica las categóricas para las distancias."""
    numeric = data[columns].select_dtypes(include="number").columns.tolist()
    categorical = [column for column in columns if column not in numeric]
    transformers = []
    if numeric:
        transformers.append(("num", StandardScaler(), numeric))
    if categorical:
        transformers.append(
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical,
            )
        )
    return ColumnTransformer(transformers, verbose_feature_names_out=False)


def score_labels(X_cluster: np.ndarray, labels: np.ndarray) -> dict:
    counts = np.bincount(labels)
    return {
        "silhouette": silhouette_score(
            X_cluster,
            labels,
            sample_size=min(SILHOUETTE_SAMPLE_SIZE, len(labels)),
            random_state=RANDOM_STATE,
        ),
        "davies_bouldin": davies_bouldin_score(X_cluster, labels),
        "calinski_harabasz": calinski_harabasz_score(X_cluster, labels),
        "min_cluster_size": int(counts.min()),
        "max_cluster_size": int(counts.max()),
        "min_cluster_pct": float(counts.min() / len(labels) * 100),
    }


def compare_feature_sets(df: pd.DataFrame) -> pd.DataFrame:
    """Evalúa adiciones y retiros individuales sobre la base actual, con k=4."""
    available = [
        column for column in df.columns if column not in {"customerID", "Churn"}
    ]
    engineered = build_model_features(df[available])
    screen_data = df.copy()
    engineered_columns = ["SecuritySupportCount", "StreamingServicesCount"]
    screen_data[engineered_columns] = engineered[engineered_columns]
    candidates = {"Base actual": BASE_CLUSTER_FEATURES.copy()}
    for column in available:
        if column not in BASE_CLUSTER_FEATURES:
            candidates[f"Base + {column}"] = [*BASE_CLUSTER_FEATURES, column]
    for column in BASE_CLUSTER_FEATURES:
        candidates[f"Base sin {column}"] = [
            item for item in BASE_CLUSTER_FEATURES if item != column
        ]
    candidates["Todas las predictoras"] = available
    for count in engineered_columns:
        candidates[f"Base + {count}"] = [*BASE_CLUSTER_FEATURES, count]
        candidates[f"Seleccion actual + {count}"] = [*CLUSTER_FEATURES, count]
    candidates["Base + ambos conteos de servicios"] = [
        *BASE_CLUSTER_FEATURES,
        *engineered_columns,
    ]
    candidates["Seleccion actual + ambos conteos"] = [
        *CLUSTER_FEATURES,
        *engineered_columns,
    ]

    churn = df["Churn"].eq("Yes").astype(int)
    rows = []
    for name, columns in candidates.items():
        transformed = make_preprocessor(screen_data, columns).fit_transform(
            screen_data[columns]
        )
        labels = KMeans(
            n_clusters=K_FEATURE_SCREEN, random_state=RANDOM_STATE, n_init=20
        ).fit_predict(transformed)
        counts = np.bincount(labels)
        churn_by_cluster = pd.DataFrame(
            {"cluster": labels, "churn": churn.to_numpy()}
        ).groupby("cluster")["churn"].mean()
        rows.append(
            {
                "candidate": name,
                "input_features": ";".join(columns),
                "n_input_features": len(columns),
                "n_encoded_features": transformed.shape[1],
                "silhouette": silhouette_score(
                    transformed,
                    labels,
                    sample_size=min(SILHOUETTE_SAMPLE_SIZE, len(labels)),
                    random_state=RANDOM_STATE,
                ),
                "davies_bouldin": davies_bouldin_score(transformed, labels),
                "calinski_harabasz": calinski_harabasz_score(transformed, labels),
                "min_cluster_pct": float(counts.min() / len(labels) * 100),
                "max_cluster_pct": float(counts.max() / len(labels) * 100),
                # Churn se resume después de asignar los clusters; no forma parte del ajuste.
                "min_cluster_churn_rate": float(churn_by_cluster.min()),
                "max_cluster_churn_rate": float(churn_by_cluster.max()),
                "cluster_churn_rate_std": float(churn_by_cluster.std()),
            }
        )
        print(f"Variables evaluadas: {name}", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el CSV limpio: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    feature_results = compare_feature_sets(df)
    FEATURE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    feature_results.to_csv(FEATURE_OUTPUT_PATH, index=False)
    print("\nComparación de variables candidatas con K-Means y k=4:")
    print(
        feature_results.sort_values("silhouette", ascending=False)
        .head(10)
        .round(3)
        .to_string(index=False)
    )
    print(f"\nComparación de variables guardada en: {FEATURE_OUTPUT_PATH}")

    X = df[CLUSTER_FEATURES].copy()
    X_cluster = make_preprocessor(X, CLUSTER_FEATURES).fit_transform(X)

    rows = []
    for k in K_VALUES:
        kmeans = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        kmeans_labels = kmeans.fit_predict(X_cluster)
        rows.append(
            {
                "algorithm": "K-Means",
                "k": k,
                "inertia": float(kmeans.inertia_),
                "aic": np.nan,
                "bic": np.nan,
                **score_labels(X_cluster, kmeans_labels),
            }
        )

        mixture = GaussianMixture(
            n_components=k,
            covariance_type="diag",
            n_init=3,
            max_iter=200,
            reg_covar=1e-6,
            random_state=RANDOM_STATE,
        )
        mixture_labels = mixture.fit_predict(X_cluster)
        rows.append(
            {
                "algorithm": "Gaussian Mixture",
                "k": k,
                "inertia": np.nan,
                "aic": float(mixture.aic(X_cluster)),
                "bic": float(mixture.bic(X_cluster)),
                **score_labels(X_cluster, mixture_labels),
            }
        )
        print(f"k={k}: K-Means y Gaussian Mixture evaluados", flush=True)

    results = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)
    print("\nComparación por algoritmo y k:")
    print(results.round(3).to_string(index=False))
    print(f"\nGuardado en: {OUTPUT_PATH}")
    print(
        f"Silhouette aproximada con la misma muestra de "
        f"{SILHOUETTE_SAMPLE_SIZE} clientes; inertia solo aplica a K-Means."
    )


if __name__ == "__main__":
    main()
