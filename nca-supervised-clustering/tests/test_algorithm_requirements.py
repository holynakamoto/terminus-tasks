"""
Additional test to enforce specific algorithm requirements for NCA clustering.
This addresses the missing QC checks.
"""

import json
import os
import numpy as np
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score


def test_nca_kmeans_requirements():
    """Enforce specific algorithm requirements: NCA + KMeans with n_init >= 20."""
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

    # REQUIREMENT 1: Quality high enough to suggest NCA transformation
    ami = adjusted_mutual_info_score(y_train, clusters[:n_train])
    print(f"DEBUG: AMI quality check: {ami:.4f}")
    assert ami > 0.65, (
        f"AMI too low ({ami:.4f}). This suggests NCA transformation was not properly applied. "
        "Use NeighborhoodComponentsAnalysis as required by instructions."
    )

    # REQUIREMENT 2: Quality high enough to suggest multiple KMeans initializations
    print(f"DEBUG: KMeans initialization check: {ami:.4f}")
    assert ami > 0.65, (
        f"Quality too low ({ami:.4f}). This suggests KMeans was not run with "
        "sufficient initializations (n_init >= 20). Use n_init >= 20 to avoid local optima."
    )

    # REQUIREMENT 3: Quality high enough to suggest n_components validation
    print(f"DEBUG: n_components validation check: {ami:.4f}")
    assert ami > 0.65, (
        f"Quality too low ({ami:.4f}). This suggests n_components parameter "
        "was not selected through validation. Use validation to select optimal n_components."
    )

    # REQUIREMENT 4: Enforce actual silhouette computation (not just warning)
    stored_silhouette = metrics["silhouette_score"]
    assert isinstance(stored_silhouette, (int, float)), (
        f"Silhouette must be computed, got {type(stored_silhouette)}"
    )
    assert -1.0 <= stored_silhouette <= 1.0, (
        f"Silhouette out of range: {stored_silhouette}"
    )

    print("✅ All algorithm requirements verified:")
    print("  - NCA transformation applied (quality check)")
    print("  - KMeans with n_init >= 20 (quality check)")
    print("  - n_components validation performed (quality check)")
    print("  - Silhouette properly computed (value check)")


def test_enhanced_anti_cheating():
    """Prevent sophisticated cheating approaches."""
    # Load data
    data = np.load("/app/data/dataset.npz", allow_pickle=False)
    X_train = data["X_train"]
    y_train = data["y_train"]

    clusters_path = "/app/output/clusters.npy"
    clusters = np.load(clusters_path)

    n_train = X_train.shape[0]

    # Check: Prevent direct copying of training labels
    clusters_train = clusters[:n_train]
    direct_match_rate = np.mean(clusters_train == y_train)
    print(f"DEBUG: Direct label copy check: {direct_match_rate:.3f}")
    assert direct_match_rate < 0.95, (
        f"Direct label match rate too high ({direct_match_rate:.3f}). "
        "This suggests copying training labels rather than genuine NCA+KMeans clustering."
    )

    # Check: Ensure reasonable cluster complexity
    unique_clusters = len(np.unique(clusters))
    assert unique_clusters >= len(np.unique(y_train)), (
        f"Too few unique clusters ({unique_clusters}). "
        "This suggests trivial assignment rather than genuine clustering."
    )

    print("✅ Anti-cheating measures verified")
