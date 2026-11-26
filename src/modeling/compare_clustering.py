"""Compara las segmentaciones de K-Means y Gaussian Mixture con las mismas variables."""

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
DATA_PATH = ROOT / "data" / "processed" / "telco_churn_clean.csv"
OUTPUT_PATH = ROOT / "data" / "output" / "clustering_model_comparison.csv"

RANDOM_STATE = 42
K_VALUES = range(2, 9)
SILHOUETTE_SAMPLE_SIZE = 2000
CLUSTER_FEATURES = ["tenure", "MonthlyCharges", "Contract"]


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


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el CSV limpio: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    X = df[CLUSTER_FEATURES].copy()
    prep = ColumnTransformer(
        [
            ("num", StandardScaler(), ["tenure", "MonthlyCharges"]),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Contract"]),
        ],
        verbose_feature_names_out=False,
    )
    X_cluster = prep.fit_transform(X)

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
