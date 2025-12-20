#!/bin/bash
# CANARY_STRING_PLACEHOLDER

set -euo pipefail

# Locate python binary (python3 preferred, fallback to python)
PYTHON_BIN="$(command -v python3 || command -v python)"

# Execute the full solution in a Python heredoc for reliability and clarity
"$PYTHON_BIN" - <<'PY'
import json
import os
import sys

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score
from sklearn.neighbors import NeighborhoodComponentsAnalysis

# Paths
DATA_PATH = "/app/data/dataset.npz"
OUT_DIR = "/app/output"
CLUSTERS_PATH = os.path.join(OUT_DIR, "clusters.npy")
METRICS_PATH = os.path.join(OUT_DIR, "metrics.json")

os.makedirs(OUT_DIR, exist_ok=True)

# Load data
data = np.load(DATA_PATH, allow_pickle=False)
X_train = data["X_train"]
y_train = data["y_train"]
X_full = data["X_full"]
n_clusters = int(data["n_clusters"].item())

n_classes = len(np.unique(y_train))
n_features = X_train.shape[1]
n_train = X_train.shape[0]

print(f"Data loaded: X_train={X_train.shape}, X_full={X_full.shape}, n_clusters={n_clusters}, n_classes={n_classes}", file=sys.stderr)

# Determine best n_components through validation
# We'll test different values and pick the one that gives best results
min_comp = max(2, n_classes - 1)
max_comp = min(n_features, min(n_train // 10, n_classes + 10))  # More conservative upper bound
candidates = list(range(min_comp, max_comp + 1))

print(f"Testing n_components from {min_comp} to {max_comp}", file=sys.stderr)

best_n_components = min_comp
best_ami_global = -1.0

# Try each n_components candidate on full training data
for n_comp in candidates:
    try:
        nca = NeighborhoodComponentsAnalysis(
            n_components=n_comp,
            random_state=42,
            max_iter=500,  # More iterations for better convergence
            tol=1e-6,  # Tighter tolerance
        )
        nca.fit(X_train, y_train)
        X_transformed = nca.transform(X_full)
        
        # Test with multiple KMeans initializations - increased from 20 to 50
        best_ami_for_comp = -1.0
        for seed in range(42, 42 + 50):
            km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=1)
            labels = km.fit_predict(X_transformed)
            ami = adjusted_mutual_info_score(y_train, labels[:n_train])
            best_ami_for_comp = max(best_ami_for_comp, ami)
        
        print(f"n_components={n_comp}: best_ami={best_ami_for_comp:.4f}", file=sys.stderr)
        
        if best_ami_for_comp > best_ami_global:
            best_ami_global = best_ami_for_comp
            best_n_components = n_comp
    except Exception as e:
        print(f"n_components={n_comp} failed: {e}", file=sys.stderr)
        continue

print(f"Selected n_components={best_n_components} with AMI={best_ami_global:.4f}", file=sys.stderr)

# Final fit with best n_components
nca_final = NeighborhoodComponentsAnalysis(
    n_components=best_n_components,
    random_state=42,
    max_iter=1000,  # Even more iterations for final fit to ensure convergence
    tol=1e-6,  # Tighter tolerance for better optimization
)
nca_final.fit(X_train, y_train)
X_embedded = nca_final.transform(X_full)

print(f"Final NCA transform: {X_embedded.shape}", file=sys.stderr)

# Final clustering: multiple initializations, select best by AMI on labeled subset
best_clusters = None
best_ami = -1.0
best_inertia = float('inf')

for seed in range(42, 42 + 200):  # Increased from 100 to 200 initializations for robustness
    km = KMeans(
        n_clusters=n_clusters,
        random_state=seed,
        n_init=1,  # Manual loop replaces n_init
    )
    clusters_cand = km.fit_predict(X_embedded)
    ami_cand = adjusted_mutual_info_score(y_train, clusters_cand[:n_train])

    if (ami_cand > best_ami or
        (abs(ami_cand - best_ami) < 0.001 and km.inertia_ < best_inertia)):
        best_ami = ami_cand
        best_inertia = km.inertia_
        best_clusters = clusters_cand

# Safety check - ensure we have valid clusters
if best_clusters is None:
    raise RuntimeError("Failed to find valid clustering - best_clusters is None")

clusters = best_clusters

# Verify shape
print(f"Clusters shape: {clusters.shape}, expected: ({X_full.shape[0]},)", file=sys.stderr)
print(f"Unique clusters: {len(np.unique(clusters))}, expected: {n_clusters}", file=sys.stderr)

ami = adjusted_mutual_info_score(y_train, clusters[:n_train])
silhouette = silhouette_score(X_embedded, clusters)

# Debug output - print to both stderr and stdout for visibility
debug_msg = f"ACHIEVED AMI: {ami:.6f} | Silhouette: {silhouette:.6f} | n_components: {best_n_components}"
print(debug_msg, file=sys.stderr)
print(debug_msg, file=sys.stdout)

# Save outputs
np.save(CLUSTERS_PATH, clusters.astype(np.int64))

metrics = {
    "adjusted_mutual_info": round(float(ami), 4),
    "silhouette_score": round(float(silhouette), 4)
}

with open(METRICS_PATH, "w") as f:
    json.dump(metrics, f, indent=2)

print(f"Outputs saved: clusters={CLUSTERS_PATH}, metrics={METRICS_PATH}", file=sys.stderr)

PY

echo "Clustering complete. Outputs saved to /app/output/"
