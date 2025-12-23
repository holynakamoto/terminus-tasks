#!/bin/bash
set -euo pipefail

# Oracle solution: NCA (fit on labeled) -> transform full -> KMeans on embedding
# Outputs:
# - /app/output/clusters.npy   (int64, shape (n_total,))
# - /app/output/embedding.npy  (float64, shape (n_total, n_components))
# - /app/output/metrics.json   (AMI on labeled subset; silhouette on embedding)

exec python3 - <<'PY'
import json
import os
import sys

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score
from sklearn.neighbors import NeighborhoodComponentsAnalysis
from sklearn.preprocessing import StandardScaler

DATA_PATH = "/app/data/dataset.npz"
OUT_DIR = "/app/output"
CLUSTERS_PATH = os.path.join(OUT_DIR, "clusters.npy")
EMBEDDING_PATH = os.path.join(OUT_DIR, "embedding.npy")
METRICS_PATH = os.path.join(OUT_DIR, "metrics.json")

RANDOM_STATE = 0


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def ensure_exact_k_clusters(labels: np.ndarray, k: int) -> np.ndarray:
    """
    Ensure labels are in [0, k-1] and that all k cluster IDs are present.
    If some IDs are missing (rare but possible if something degenerates),
    deterministically reassign a few points to cover missing IDs.

    This keeps the output valid for tests that require exactly n_clusters unique IDs.
    """
    labels = labels.astype(np.int64, copy=True)

    # Force into range first (defensive)
    labels = np.clip(labels, 0, k - 1)

    present = set(map(int, np.unique(labels)))
    missing = [c for c in range(k) if c not in present]
    if not missing:
        return labels

    # Deterministically choose indices to reassign: earliest indices not already used.
    # This is simple and reproducible.
    for i, c in enumerate(missing):
        labels[i] = int(c)

    return labels


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    data = np.load(DATA_PATH, allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_full = data["X_full"]
    n_clusters = int(np.asarray(data["n_clusters"]).item())

    n_train = int(X_train.shape[0])
    n_total = int(X_full.shape[0])
    n_features = int(X_full.shape[1])

    # Choose a deterministic n_components >= 2 and <= n_features
    # (No requirement to validate; tests require embedding >=2D for silhouette.)
    n_components = min(16, n_features)
    if n_components < 2:
        n_components = 2

    eprint(
        f"Loaded data: X_train={X_train.shape}, X_full={X_full.shape}, n_clusters={n_clusters}"
    )
    eprint(f"Using n_components={n_components}")

    # Preprocess (recommended): scale using labeled data only to avoid leakage.
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_full_s = scaler.transform(X_full)

    # Fit NCA on labeled data only
    nca = NeighborhoodComponentsAnalysis(
        n_components=n_components,
        random_state=RANDOM_STATE,
        max_iter=300,
        tol=1e-5,
    )
    nca.fit(X_train_s, y_train)

    # Transform full dataset
    embedding = nca.transform(X_full_s).astype(np.float64)

    # Cluster on embedding
    kmeans = KMeans(
        n_clusters=n_clusters,
        n_init=20,
        random_state=RANDOM_STATE,
    )
    clusters = kmeans.fit_predict(embedding).astype(np.int64)
    clusters = ensure_exact_k_clusters(clusters, n_clusters)

    # Metrics
    ami = adjusted_mutual_info_score(y_train, clusters[:n_train])
    sil = silhouette_score(embedding, clusters)

    metrics = {
        "adjusted_mutual_info": round(float(ami), 4),
        "silhouette_score": round(float(sil), 4),
    }

    # Save outputs
    np.save(CLUSTERS_PATH, clusters.astype(np.int64))
    np.save(EMBEDDING_PATH, embedding)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    eprint(f"Saved {CLUSTERS_PATH}")
    eprint(f"Saved {EMBEDDING_PATH}")
    eprint(f"Saved {METRICS_PATH}")
    eprint(f"AMI(labeled)={ami:.6f} Silhouette(embedding)={sil:.6f}")


if __name__ == "__main__":
    main()
    print("Clustering complete. Outputs saved to /app/output/")
PY
