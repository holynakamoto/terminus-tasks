"""
Pytest tests for the NCA-supervised clustering task.

Goal of these tests:
- Verify required outputs exist and have correct shapes/dtypes.
- Verify an NCA embedding for the full dataset is produced (embedding.npy).
- Verify clustering is performed on the embedding (not raw features).
- Verify metrics.json is computed correctly (AMI on labeled subset only; silhouette on embedding),
  and rounded to exactly 4 decimals.
- Avoid brittle "quality thresholds" (e.g., AMI > X) that can make tasks unfair/unsolvable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score

# ---------------------------
# Helpers
# ---------------------------


def _load_dataset() -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_full = data["X_full"]
    n_clusters = int(np.asarray(data["n_clusters"]).item())
    return X_train, y_train, X_full, n_clusters


def _load_outputs() -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    clusters_path = "/app/output/clusters.npy"
    embedding_path = "/app/output/embedding.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path)
    embedding = np.load(embedding_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return clusters, embedding, metrics


def _assert_rounded_4dp(x: Any, name: str) -> None:
    assert isinstance(x, (int, float)), f"{name} must be a number, got {type(x)}"
    xf = float(x)
    assert round(xf, 4) == xf, f"{name} must be rounded to exactly 4 decimals, got {x}"


def _assert_finite_array(arr: np.ndarray, name: str) -> None:
    assert np.isfinite(arr).all(), f"{name} contains non-finite values (NaN/inf)"


# ---------------------------
# Existence + basic format
# ---------------------------


def test_required_files_exist():
    for path in (
        "/app/output/clusters.npy",
        "/app/output/embedding.npy",
        "/app/output/metrics.json",
    ):
        assert os.path.exists(path), f"Missing required output file: {path}"


def test_clusters_shape_dtype_and_range():
    X_train, y_train, X_full, n_clusters = _load_dataset()
    clusters, embedding, metrics = _load_outputs()

    assert clusters.shape == (X_full.shape[0],), (
        f"clusters.npy must have shape ({X_full.shape[0]},), got {clusters.shape}"
    )
    assert np.issubdtype(clusters.dtype, np.integer), (
        f"clusters.npy must be integer dtype, got {clusters.dtype}"
    )

    # Range and cardinality requirements
    assert clusters.min() >= 0, "Cluster IDs must be non-negative"
    assert clusters.max() < n_clusters, (
        f"Cluster IDs must be < n_clusters ({n_clusters}), got max={clusters.max()}"
    )
    assert len(np.unique(clusters)) == n_clusters, (
        f"Expected exactly {n_clusters} unique cluster IDs, got {len(np.unique(clusters))}"
    )


def test_embedding_shape_dtype_and_finite():
    _, _, X_full, n_clusters = _load_dataset()
    clusters, embedding, metrics = _load_outputs()

    assert embedding.ndim == 2, (
        f"embedding.npy must be 2D array, got shape {embedding.shape}"
    )
    assert embedding.shape[0] == X_full.shape[0], (
        f"embedding.npy first dimension must match X_full rows ({X_full.shape[0]}), got {embedding.shape[0]}"
    )

    # Should be numeric and finite
    assert np.issubdtype(embedding.dtype, np.floating), (
        f"embedding.npy should be floating dtype, got {embedding.dtype}"
    )
    _assert_finite_array(embedding, "embedding.npy")

    # Must have at least 2 components for silhouette_score to be defined in a meaningful way
    assert embedding.shape[1] >= 2, (
        f"embedding.npy must have at least 2 dimensions/components, got {embedding.shape[1]}"
    )


def test_metrics_json_structure_and_rounding():
    _, _, _, _ = _load_dataset()
    _, _, metrics = _load_outputs()

    assert isinstance(metrics, dict), "metrics.json must be a JSON object"
    assert "adjusted_mutual_info" in metrics, (
        "metrics.json must include 'adjusted_mutual_info'"
    )
    assert "silhouette_score" in metrics, "metrics.json must include 'silhouette_score'"

    _assert_rounded_4dp(metrics["adjusted_mutual_info"], "adjusted_mutual_info")
    _assert_rounded_4dp(metrics["silhouette_score"], "silhouette_score")

    # Basic valid ranges
    ami = float(metrics["adjusted_mutual_info"])
    sil = float(metrics["silhouette_score"])
    assert -1.0 <= ami <= 1.0, f"adjusted_mutual_info must be in [-1, 1], got {ami}"
    assert -1.0 <= sil <= 1.0, f"silhouette_score must be in [-1, 1], got {sil}"


# ---------------------------
# Correct metric computation
# ---------------------------


def test_metrics_match_recomputed_values():
    X_train, y_train, X_full, n_clusters = _load_dataset()
    clusters, embedding, metrics = _load_outputs()

    n_train = X_train.shape[0]

    # AMI must be computed on labeled subset only
    ami_recomputed = adjusted_mutual_info_score(y_train, clusters[:n_train])
    ami_expected = round(float(ami_recomputed), 4)
    assert abs(float(metrics["adjusted_mutual_info"]) - ami_expected) < 1e-4, (
        f"adjusted_mutual_info must equal AMI(y_train, clusters[:n_train]) rounded to 4dp. "
        f"Expected {ami_expected}, got {metrics['adjusted_mutual_info']}"
    )

    # Silhouette must be computed on the embedding (not raw features)
    sil_recomputed = silhouette_score(embedding, clusters)
    sil_expected = round(float(sil_recomputed), 4)
    assert abs(float(metrics["silhouette_score"]) - sil_expected) < 1e-4, (
        f"silhouette_score must equal silhouette_score(embedding, clusters) rounded to 4dp. "
        f"Expected {sil_expected}, got {metrics['silhouette_score']}"
    )


def test_silhouette_not_computed_on_raw_features():
    """
    Ensure silhouette is not computed on raw X_full.

    We can't prove intent, but we can check that the stored silhouette matches the embedding-based
    recomputation (tested elsewhere) AND is meaningfully different from the raw-feature silhouette
    in typical cases.
    """
    _, _, X_full, _ = _load_dataset()
    clusters, embedding, metrics = _load_outputs()

    stored = float(metrics["silhouette_score"])
    raw = round(float(silhouette_score(X_full, clusters)), 4)

    # If they are identical to 4dp, it's very likely silhouette was computed on raw features.
    # Allow an exception only if both are near-zero (degenerate case).
    if abs(stored) >= 0.05 or abs(raw) >= 0.05:
        assert stored != raw, (
            f"Stored silhouette ({stored}) matches raw-feature silhouette ({raw}) to 4dp. "
            "Silhouette must be computed on the NCA embedding, not raw features."
        )


# ---------------------------
# Verify clustering uses the embedding
# ---------------------------


def test_kmeans_on_embedding_reproduces_clusters_reasonably():
    """
    Verify that clusters are consistent with running KMeans on the saved embedding.

    Because KMeans depends on initialization, we don't require exact equality with a single run.
    Instead, we require that a deterministic KMeans (fixed random_state, sufficiently large n_init)
    on the embedding yields a clustering that is highly aligned with the provided clustering (AMI high).

    This avoids enforcing a particular random_state in user code while still ensuring the embedding
    is actually used for clustering.
    """
    _, _, _, n_clusters = _load_dataset()
    clusters, embedding, metrics = _load_outputs()

    km = KMeans(n_clusters=n_clusters, n_init=50, random_state=0)
    repro = km.fit_predict(embedding).astype(np.int64)

    # Compare the provided clustering to the recomputed clustering using AMI (perm-invariant)
    ami_between = adjusted_mutual_info_score(clusters, repro)

    # This is not a "dataset difficulty" threshold; it's a pipeline-consistency check.
    # If user clustered on raw features or did something unrelated, this tends to be very low.
    assert ami_between >= 0.80, (
        f"clusters.npy does not appear to come from KMeans on embedding.npy. "
        f"AMI(clusters, KMeans(embedding))={ami_between:.4f} is too low."
    )


# ---------------------------
# Determinism and coherence checks
# ---------------------------


def test_outputs_are_deterministic_on_reload():
    """
    Ensure outputs are stable when reloaded (basic determinism and no nondeterministic write).
    """
    clusters1, embedding1, metrics1 = _load_outputs()
    clusters2, embedding2, metrics2 = _load_outputs()

    np.testing.assert_array_equal(
        clusters1, clusters2, err_msg="clusters.npy must be stable on reload"
    )
    np.testing.assert_array_equal(
        embedding1, embedding2, err_msg="embedding.npy must be stable on reload"
    )
    assert metrics1 == metrics2, "metrics.json must be stable on reload"


def test_cluster_coherence_nearest_labeled_neighbor_baseline():
    """
    Light anti-cheating / sanity check:
    Unlabeled points should not be assigned completely arbitrarily relative to labeled neighbors.
    We compute the nearest labeled neighbor in RAW space and expect some agreement.
    This is not meant to be overly strict; it just catches trivial random labeling.
    """
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    X_full = data["X_full"]
    n_train = X_train.shape[0]

    clusters = np.load("/app/output/clusters.npy").astype(np.int64)
    if X_full.shape[0] <= n_train:
        return

    X_labeled = X_full[:n_train]
    X_unlabeled = X_full[n_train:]
    clusters_labeled = clusters[:n_train]
    clusters_unlabeled = clusters[n_train:]

    from sklearn.metrics.pairwise import euclidean_distances

    distances = euclidean_distances(X_unlabeled, X_labeled)
    nearest = np.argmin(distances, axis=1)
    nearest_clusters = clusters_labeled[nearest]
    agreement = float(np.mean(clusters_unlabeled == nearest_clusters))

    # Very lenient: just avoid "totally random" (chance is ~1/n_clusters = 12.5% for 8 clusters).
    assert agreement >= 0.20, (
        f"Unlabeled-to-labeled neighbor coherence too low ({agreement:.2%}). "
        "This suggests cluster assignments may be arbitrary."
    )


def test_embedding_is_not_raw_features():
    """
    Ensure embedding.npy is not just a copy of raw features.

    NCA transforms features; even if n_components == n_features, the transform should generally
    differ from raw input. We check that embedding is not exactly equal to X_full to numerical
    tolerance.
    """
    _, _, X_full, _ = _load_dataset()
    _, embedding, _ = _load_outputs()

    # If embedding has different dimensionality, it's definitely not raw.
    if embedding.shape[1] != X_full.shape[1]:
        return

    # Otherwise, ensure it isn't identical.
    assert not np.allclose(embedding, X_full, rtol=0.0, atol=0.0), (
        "embedding.npy appears to be exactly equal to raw X_full. "
        "embedding.npy must be the NCA-transformed embedding."
    )
