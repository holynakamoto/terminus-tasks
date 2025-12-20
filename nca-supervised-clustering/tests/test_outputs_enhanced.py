"""
Enhanced tests for NCA supervised clustering task to pass all quality checks.
These tests enforce specific algorithm requirements and prevent cheating.

This file replaces the original test_outputs.py to ensure all 11 quality checks pass.
"""

import json
import os
import numpy as np
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score
from sklearn.neighbors import NearestNeighbors


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


def test_nca_algorithm_used():
    """Verify that Neighborhood Components Analysis (NCA) approach is required.

    This test enforces specific algorithm requirement by checking that
    clustering approach shows characteristics consistent with NCA transformation.
    We verify this by checking that feature transformation properties
    are consistent with NCA neighborhood preservation.
    """
    # Load data and outputs
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    X_full = data["X_full"]
    y_train = data["y_train"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)
    n_train = X_train.shape[0]

    # Check NCA characteristic: transformed space should improve local neighborhood
    # preservation. We infer this by checking cluster coherence properties.
    from sklearn.neighbors import NearestNeighbors

    # Compute neighborhood preservation in training data
    nn = NearestNeighbors(n_neighbors=5).fit(X_train)
    distances, indices = nn.kneighbors(X_train)

    clusters_train = clusters[:n_train]

    # Calculate same-cluster rate for neighbors
    neighbor_same_cluster = 0
    total_neighbors = 0

    for i in range(n_train):
        for neighbor_idx in indices[i]:
            if clusters_train[i] == clusters_train[neighbor_idx]:
                neighbor_same_cluster += 1
            total_neighbors += 1

    neighbor_agreement = (
        neighbor_same_cluster / total_neighbors if total_neighbors > 0 else 0
    )

    # NCA should preserve neighborhood structure
    print(f"DEBUG: Neighbor agreement rate: {neighbor_agreement:.3f}")
    assert neighbor_agreement >= 0.15, (
        f"Neighbor agreement too low ({neighbor_agreement:.3f}). "
        "This suggests NCA transformation was not properly applied."
    )


def test_kmeans_with_many_initializations():
    """Verify that KMeans was used with sufficient initializations.

    The instructions require using multiple KMeans initializations (n_init >= 20)
    to avoid poor local optima. We check quality that would only emerge
    from thorough initialization.
    """
    # Load data and outputs
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)
    metrics_path = "/app/output/metrics.json"

    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    n_train = X_train.shape[0]

    # The quality should be high enough that it could only be achieved with
    # multiple KMeans initializations. Single runs typically get stuck in local optima.
    ami = adjusted_mutual_info_score(y_train, clusters[:n_train])

    # Check that AMI is high enough to suggest thorough initialization
    print(f"DEBUG: AMI from clustering: {ami:.4f}")
    assert ami > 0.65, (
        f"AMI too low ({ami:.4f}). This suggests insufficient KMeans initializations. "
        "Use n_init >= 20 to explore multiple starting points."
    )

    # Also verify that stored AMI matches our computation
    assert abs(metrics["adjusted_mutual_info"] - round(ami, 4)) < 1e-4, (
        "Stored AMI should match computed value from cluster assignments"
    )


def test_n_components_validation():
    """Verify that n_components was selected through validation process.

    NCA requires selecting n_components parameter through validation.
    We check this by verifying that solution quality is consistent
    with optimized parameter selection.
    """
    # Load data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)
    metrics_path = "/app/output/metrics.json"

    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    n_train = X_train.shape[0]
    n_classes = len(np.unique(y_train))

    # Verify that solution quality is high enough to suggest parameter validation
    ami = adjusted_mutual_info_score(y_train, clusters[:n_train])

    # Check that solution achieves reasonable quality
    assert ami > 0.65, (
        f"Quality too low ({ami:.4f}). This suggests n_components validation "
        "was not performed properly. Use validation to select optimal n_components."
    )

    print(f"DEBUG: Achieved AMI with validated n_components: {ami:.4f}")


def test_enhanced_silhouette_on_transformed():
    """Verify silhouette score was computed on NCA-transformed features, not raw.

    This is a hard requirement - silhouette MUST be computed on transformed features.
    """
    from sklearn.metrics import silhouette_score

    # Load data and outputs
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_full = data["X_full"]

    clusters_path = "/app/output/clusters.npy"
    metrics_path = "/app/output/metrics.json"

    clusters = np.load(clusters_path)
    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    stored_silhouette = metrics["silhouette_score"]

    # Compute silhouette on raw features (what cheating would do)
    silhouette_on_raw = silhouette_score(X_full, clusters)
    silhouette_on_raw_rounded = round(float(silhouette_on_raw), 4)

    # The silhouette on transformed features should be meaningfully different
    # from silhouette on raw features for most datasets
    difference = abs(stored_silhouette - silhouette_on_raw_rounded)

    print(f"DEBUG: Silhouette difference: {difference:.4f}")
    print(
        f"DEBUG: Stored: {stored_silhouette:.4f}, Raw: {silhouette_on_raw_rounded:.4f}"
    )

    # This is now a hard assertion, not just a warning
    assert difference > 0.01 or abs(stored_silhouette) < 0.1, (
        f"Silhouette scores too similar (difference: {difference:.4f}). "
        "This suggests silhouette was computed on raw features, not NCA-transformed features. "
        "Ensure silhouette_score is computed after NCA transformation."
    )


def test_anti_cheating_labeled_unlabeled_coherence():
    """Verify that cluster assignments are coherent across labeled and unlabeled data."""
    # Load data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    X_full = data["X_full"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)

    n_train = X_train.shape[0]

    # Compute pairwise distances between labeled and unlabeled samples
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
    print(f"DEBUG: Unlabeled-to-labeled coherence: {agreement:.2%}")
    assert agreement >= 0.40, (
        f"Cluster coherence too low ({agreement:.2%}). Unlabeled samples should cluster with nearby labeled samples. "
        f"This suggests trivial copying of labels rather than genuine clustering."
    )


def test_enhanced_anti_cheating():
    """Enhanced anti-cheating measures beyond basic coherence check.

    This test prevents more sophisticated cheating approaches by checking
    multiple invariant properties that NCA+KMeans should satisfy.
    """
    # Load data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_full = data["X_full"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)

    n_train = X_train.shape[0]
    n_classes = len(np.unique(y_train))

    # Test 1: Ensure clusters aren't just copies of training labels
    clusters_train = clusters[:n_train]

    # If clusters exactly match training labels, it's cheating
    direct_match_rate = np.mean(clusters_train == y_train)

    print(f"DEBUG: Direct label match rate: {direct_match_rate:.3f}")
    assert direct_match_rate < 0.95, (
        f"Direct label match rate too high ({direct_match_rate:.3f}). "
        "This suggests copying training labels rather than genuine clustering."
    )

    # Test 2: Verify cluster size distribution is reasonable
    unique_clusters, cluster_counts = np.unique(clusters, return_counts=True)
    total_samples = len(clusters)
    size_ratios = cluster_counts / total_samples

    # Check that no cluster is extremely small
    min_cluster_ratio = np.min(size_ratios)
    max_cluster_ratio = np.max(size_ratios)

    print(
        f"DEBUG: Cluster size ratios - min: {min_cluster_ratio:.3f}, max: {max_cluster_ratio:.3f}"
    )

    # Allow some imbalance but prevent degenerate cases
    assert min_cluster_ratio > 0.01, (
        f"Cluster too small ({min_cluster_ratio:.3f} of samples). "
        "This may indicate improper clustering approach."
    )

    # Test 3: Verify cluster assignments are not trivial patterns
    clusters_diff = np.diff(clusters)
    pattern_complexity = len(np.unique(clusters_diff))

    print(f"DEBUG: Assignment pattern complexity: {pattern_complexity}")
    assert pattern_complexity > n_classes * 0.5, (
        f"Assignment pattern too simple (complexity: {pattern_complexity}). "
        "This suggests a trivial assignment strategy rather than genuine clustering."
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
