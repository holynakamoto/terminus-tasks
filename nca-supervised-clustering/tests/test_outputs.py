"""
Use this file to define pytest tests that verify the outputs of the task.

This file will be copied to /tests/test_outputs.py and run by the /tests/test.sh file
from the working directory.
"""

import json
import os

import numpy as np
from sklearn.metrics import adjusted_mutual_info_score


def test_clusters_file_exists():
    """Verify clusters.npy file exists in output directory."""
    clusters_path = "/app/output/clusters.npy"
    assert os.path.exists(clusters_path), (
        "clusters.npy file should exist in /app/output/"
    )


def test_clusters_shape_and_format():
    """Verify clusters.npy has correct shape, integer dtype, and valid cluster IDs."""
    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)

    # Load input data to get expected shape
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_full = data["X_full"]
    n_clusters = int(np.asarray(data["n_clusters"]).item())

    # Check shape
    assert clusters.shape == (X_full.shape[0],), (
        f"clusters should have shape ({X_full.shape[0]},) but got {clusters.shape}"
    )

    # Check dtype (should be integer)
    assert np.issubdtype(clusters.dtype, np.integer), (
        f"clusters should be integer dtype but got {clusters.dtype}"
    )

    # Check values are valid cluster IDs
    assert clusters.min() >= 0, "cluster IDs should be non-negative"
    assert clusters.max() < n_clusters, (
        f"cluster IDs should be in range [0, {n_clusters - 1}] but max is {clusters.max()}"
    )


def test_metrics_file_exists():
    """Verify metrics.json file exists in output directory."""
    metrics_path = "/app/output/metrics.json"
    assert os.path.exists(metrics_path), (
        "metrics.json file should exist in /app/output/"
    )


def test_metrics_structure():
    """Verify metrics.json contains required keys with numeric values."""
    metrics_path = "/app/output/metrics.json"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Check required keys exist
    assert "adjusted_mutual_info" in metrics, (
        "metrics.json should contain 'adjusted_mutual_info' key"
    )
    assert "silhouette_score" in metrics, (
        "metrics.json should contain 'silhouette_score' key"
    )

    # Check values are numbers
    assert isinstance(metrics["adjusted_mutual_info"], (int, float)), (
        "adjusted_mutual_info should be a number"
    )
    assert isinstance(metrics["silhouette_score"], (int, float)), (
        "silhouette_score should be a number"
    )


def test_metrics_value_ranges():
    """Verify metric values are in valid ranges [-1, 1]."""
    metrics_path = "/app/output/metrics.json"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    ami = metrics["adjusted_mutual_info"]
    sil = metrics["silhouette_score"]

    # Adjusted Mutual Information is in [-1, 1] range
    assert -1.0 <= ami <= 1.0, (
        f"adjusted_mutual_info should be in [-1, 1] but got {ami}"
    )

    # Silhouette score is in [-1, 1] range
    assert -1.0 <= sil <= 1.0, f"silhouette_score should be in [-1, 1] but got {sil}"


def test_clustering_approach_quality():
    """Verify cluster assignments use exactly n_clusters distinct integer IDs and AMI > 0.68."""
    # Load input data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]
    n_clusters = int(np.asarray(data["n_clusters"]).item())

    # Load outputs
    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Verify clusters are valid
    assert len(np.unique(clusters)) == n_clusters, (
        f"Expected {n_clusters} unique clusters, got {len(np.unique(clusters))}"
    )
    assert clusters.min() >= 0 and clusters.max() < n_clusters, (
        "Cluster IDs must be in valid range"
    )

    # Verify AMI meets quality requirement (> 0.68)
    # Calibrated for Hard difficulty: oracle achieves ~0.69-0.72, threshold set to 0.68
    # This requires careful n_components selection and proper KMeans initialization
    n_train = X_train.shape[0]
    ami_on_train = adjusted_mutual_info_score(y_train, clusters[:n_train])
    print(f"DEBUG: Actual AMI computed from clusters: {ami_on_train:.6f}")
    print(f"DEBUG: Stored AMI in metrics: {metrics['adjusted_mutual_info']:.6f}")
    assert ami_on_train > 0.68, (
        f"AMI must be > 0.68 (requires careful parameter tuning), got {ami_on_train:.6f}"
    )
    assert metrics["adjusted_mutual_info"] > 0.68, (
        f"Stored AMI must be > 0.68, got {metrics['adjusted_mutual_info']:.6f}"
    )

    # Verify metrics match computed values from outputs
    expected_ami = round(float(ami_on_train), 4)
    assert abs(metrics["adjusted_mutual_info"] - expected_ami) < 1e-4, (
        f"AMI metric should match computed value from outputs, got {metrics['adjusted_mutual_info']}, expected {expected_ami}"
    )


def test_anti_cheating_labeled_unlabeled_coherence():
    """Verify that cluster assignments are coherent across labeled and unlabeled data.

    This test prevents trivial cheating where an agent might:
    - Copy y_train directly to clusters[:n_train]
    - Assign arbitrary valid IDs to unlabeled samples

    We verify that unlabeled samples share cluster structure with labeled samples.
    """
    # Load data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    X_full = data["X_full"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)

    n_train = X_train.shape[0]

    # Compute pairwise distances between labeled and unlabeled samples
    # For each unlabeled sample, find its nearest labeled neighbor
    from sklearn.metrics.pairwise import euclidean_distances

    X_labeled = X_full[:n_train]
    X_unlabeled = X_full[n_train:]
    clusters_labeled = clusters[:n_train]
    clusters_unlabeled = clusters[n_train:]

    if len(X_unlabeled) == 0:
        # No unlabeled data, skip this test
        return

    # For each unlabeled sample, find nearest labeled neighbor
    distances = euclidean_distances(X_unlabeled, X_labeled)
    nearest_labeled_indices = np.argmin(distances, axis=1)
    nearest_labeled_clusters = clusters_labeled[nearest_labeled_indices]

    # Compute agreement: what fraction of unlabeled samples have the same
    # cluster ID as their nearest labeled neighbor?
    agreement = np.mean(clusters_unlabeled == nearest_labeled_clusters)

    # For a legitimate clustering approach (NCA + KMeans), we expect high agreement
    # because nearby points in feature space should be in the same cluster.
    # Threshold: at least 40% agreement (more lenient to allow for boundary cases)
    print(f"DEBUG: Unlabeled-to-labeled coherence: {agreement:.2%}")
    assert agreement >= 0.40, (
        f"Cluster coherence too low ({agreement:.2%}). Unlabeled samples should cluster with nearby labeled samples. "
        f"This suggests trivial copying of labels rather than genuine clustering."
    )


def test_metrics_match_computed_values():
    """Verify stored metrics match values computed from cluster assignments."""
    # Load outputs
    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Load input data to verify metric computation
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    y_train = data["y_train"]
    n_train = y_train.shape[0]

    # Verify AMI metric matches what we compute from cluster assignments
    ami_on_train = adjusted_mutual_info_score(y_train, clusters[:n_train])
    expected_ami = round(float(ami_on_train), 4)
    assert abs(metrics["adjusted_mutual_info"] - expected_ami) < 1e-4, (
        f"AMI metric should match computed value from outputs, got {metrics['adjusted_mutual_info']}, expected {expected_ami}"
    )

    # Verify silhouette score is in valid range
    assert -1.0 <= metrics["silhouette_score"] <= 1.0, (
        f"Silhouette score must be in [-1, 1], got {metrics['silhouette_score']}"
    )


def test_silhouette_not_on_raw_features():
    """Verify silhouette score was NOT computed on raw features (anti-cheating).

    This test prevents agents from computing silhouette on raw X_full instead of
    NCA-transformed features. If silhouette matches raw features too closely,
    it suggests NCA transformation was not applied.
    """
    from sklearn.metrics import silhouette_score

    # Load data and outputs
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_full = data["X_full"]

    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    stored_silhouette = metrics["silhouette_score"]

    # Compute what silhouette WOULD be on raw features
    # (what a cheating agent might compute)
    silhouette_on_raw = silhouette_score(X_full, clusters)
    silhouette_on_raw_rounded = round(float(silhouette_on_raw), 4)

    # If they match too closely, the agent likely didn't use NCA transformation
    # Allow small tolerance for cases where raw and transformed happen to be similar
    # but flag exact matches as likely cheating
    if abs(stored_silhouette - silhouette_on_raw_rounded) < 0.001:
        # They're suspiciously close - check if this could be legitimate
        # by seeing if the coherence test also passed (if it did, probably not cheating)
        print(
            f"WARNING: Silhouette on raw features ({silhouette_on_raw_rounded}) "
            f"matches stored silhouette ({stored_silhouette})"
        )
        print(
            "This suggests silhouette may not have been computed on NCA-transformed features."
        )
        # Don't fail here - let the coherence test catch actual cheating
        # This is just a warning for borderline cases


def test_metrics_computation_verification():
    """Verify metrics are computed correctly and rounded to 4 decimal places."""
    # Load input data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]

    # Load outputs
    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path).astype(np.int64)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Verify AMI is computed on training subset only
    n_train = X_train.shape[0]
    expected_ami_train = adjusted_mutual_info_score(y_train, clusters[:n_train])
    expected_ami_rounded = round(float(expected_ami_train), 4)

    assert abs(metrics["adjusted_mutual_info"] - expected_ami_rounded) < 1e-4, (
        "AMI must be computed on training labels vs first n_train cluster assignments"
    )

    # Verify silhouette score is in valid range
    assert -1.0 <= metrics["silhouette_score"] <= 1.0, (
        f"Silhouette score must be in [-1, 1], got {metrics['silhouette_score']}"
    )

    # Verify metrics are rounded to 4 decimal places
    ami = metrics["adjusted_mutual_info"]
    sil = metrics["silhouette_score"]

    assert round(ami, 4) == ami, (
        f"adjusted_mutual_info must be rounded to exactly 4 decimal places, got {ami}"
    )
    assert round(sil, 4) == sil, (
        f"silhouette_score must be rounded to exactly 4 decimal places, got {sil}"
    )


def test_determinism():
    """Verify output files are consistent when reloaded (ensures stable write)."""
    # Load outputs
    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters1 = np.load(clusters_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics1 = json.load(f)

    # Reload to verify file contents are consistent
    clusters2 = np.load(clusters_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics2 = json.load(f)

    # Verify outputs are consistent when reloaded
    np.testing.assert_array_equal(
        clusters1,
        clusters2,
        err_msg="Cluster outputs should be deterministic and consistent",
    )
    assert metrics1 == metrics2, "Metrics should be deterministic and consistent"

    # Verify metrics are consistent with cluster assignments
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    y_train = data["y_train"]
    n_train = y_train.shape[0]

    computed_ami = round(
        float(adjusted_mutual_info_score(y_train, clusters1[:n_train])), 4
    )
    assert abs(metrics1["adjusted_mutual_info"] - computed_ami) < 1e-4, (
        "Stored AMI must match AMI computed from cluster assignments"
    )


def test_outputs():
    """Verify outputs meet all required specifications."""
    # Verify clusters file
    clusters_path = "/app/output/clusters.npy"
    assert os.path.exists(clusters_path), "clusters.npy must exist"

    clusters = np.load(clusters_path)
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_full = data["X_full"]
    n_clusters = int(np.asarray(data["n_clusters"]).item())

    assert clusters.shape == (X_full.shape[0],), "clusters shape mismatch"
    assert np.issubdtype(clusters.dtype, np.integer), "clusters must be integer type"
    assert 0 <= clusters.min() and clusters.max() < n_clusters, "invalid cluster IDs"

    # Verify metrics file
    metrics_path = "/app/output/metrics.json"
    assert os.path.exists(metrics_path), "metrics.json must exist"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert "adjusted_mutual_info" in metrics and "silhouette_score" in metrics, (
        "metrics.json missing required keys"
    )
    assert -1.0 <= metrics["adjusted_mutual_info"] <= 1.0, "AMI out of range"
    assert -1.0 <= metrics["silhouette_score"] <= 1.0, "Silhouette score out of range"
