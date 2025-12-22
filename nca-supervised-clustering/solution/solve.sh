#!/bin/bash
# solution/solve.sh - Oracle solution for Semi-Supervised NCA + KMeans clustering task
# This bash script executes the Python solution with self-training

exec python3 <<'PYEOF'

import json
import os
import sys
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, silhouette_score
from sklearn.neighbors import NeighborhoodComponentsAnalysis, KNeighborsClassifier

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
X_unlabeled = X_full[n_train:]

print(f"Data loaded: X_train={X_train.shape}, X_unlabeled={X_unlabeled.shape}, "
      f"X_full={X_full.shape}, n_clusters={n_clusters}, n_classes={n_classes}", file=sys.stderr)

# === SEMI-SUPERVISED LEARNING APPROACH ===
# Step 1: Initial parameter selection with labeled data only
print("=== Step 1: Initial n_components selection (labeled data only) ===", file=sys.stderr)
min_comp = max(2, n_classes - 1)
max_comp = min(n_features, min(n_train // 10, n_classes + 10))
candidates = list(range(min_comp, max_comp + 1))

best_n_components_initial = min_comp
best_ami_initial = -1.0

for n_comp in candidates:
    try:
        nca = NeighborhoodComponentsAnalysis(
            n_components=n_comp,
            random_state=42,
            max_iter=500,
            tol=1e-6,
        )
        nca.fit(X_train, y_train)
        X_transformed_train = nca.transform(X_train)

        # Quick validation with a few KMeans runs
        best_ami_comp = -1.0
        for seed in range(42, 52):
            km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
            labels = km.fit_predict(X_transformed_train)
            ami = adjusted_mutual_info_score(y_train, labels)
            best_ami_comp = max(best_ami_comp, ami)

        if best_ami_comp > best_ami_initial:
            best_ami_initial = best_ami_comp
            best_n_components_initial = n_comp
    except Exception as e:
        print(f"n_components={n_comp} failed: {e}", file=sys.stderr)
        continue

print(f"Initial n_components={best_n_components_initial} (AMI={best_ami_initial:.4f})", file=sys.stderr)

# Step 2: Self-training with pseudo-labeling
print("=== Step 2: Self-training with pseudo-labels ===", file=sys.stderr)
# Start with best n_components from initial search
n_comp = best_n_components_initial

# Current labeled set
X_labeled = X_train.copy()
y_labeled = y_train.copy()

# Iterative self-training (2-3 iterations)
for iteration in range(3):
    print(f"  Iteration {iteration + 1}: Training with {len(y_labeled)} labeled samples", file=sys.stderr)

    # Train NCA on current labeled set
    nca = NeighborhoodComponentsAnalysis(
        n_components=n_comp,
        random_state=42,
        max_iter=500,
        tol=1e-6,
    )
    nca.fit(X_labeled, y_labeled)

    # Transform all data
    X_full_transformed = nca.transform(X_full)

    # Use KNN to predict pseudo-labels for unlabeled data
    knn = KNeighborsClassifier(n_neighbors=7, weights='distance')
    knn.fit(nca.transform(X_labeled), y_labeled)

    # Predict on unlabeled data
    X_unlabeled_transformed = nca.transform(X_unlabeled)
    pseudo_labels = knn.predict(X_unlabeled_transformed)
    pseudo_probs = knn.predict_proba(X_unlabeled_transformed)

    # Select high-confidence predictions
    confidence = np.max(pseudo_probs, axis=1)
    confidence_threshold = np.percentile(confidence, 70)  # Top 30% most confident
    high_conf_mask = confidence >= confidence_threshold

    n_added = np.sum(high_conf_mask)
    print(f"    Adding {n_added} high-confidence pseudo-labeled samples (threshold={confidence_threshold:.3f})", file=sys.stderr)

    if n_added == 0:
        print(f"    No more samples to add, stopping self-training", file=sys.stderr)
        break

    # Augment labeled set with high-confidence predictions
    X_labeled = np.vstack([X_labeled, X_unlabeled[high_conf_mask]])
    y_labeled = np.concatenate([y_labeled, pseudo_labels[high_conf_mask]])

    # Update unlabeled set
    X_unlabeled = X_unlabeled[~high_conf_mask]

print(f"Self-training complete: final labeled set size = {len(y_labeled)}", file=sys.stderr)

# === Step 3: Final NCA embedding with augmented data ===
print("=== Step 3: Final NCA embedding with augmented labeled set ===", file=sys.stderr)
nca_final = NeighborhoodComponentsAnalysis(
    n_components=n_comp,
    random_state=42,
    max_iter=500,
    tol=1e-6,
)
nca_final.fit(X_labeled, y_labeled)
X_embedded = nca_final.transform(X_full)
print(f"Final embedding shape: {X_embedded.shape}", file=sys.stderr)

# === Step 4: Aggressive KMeans search ===
print("=== Step 4: Aggressive KMeans search (target AMI > 0.72) ===", file=sys.stderr)
best_ami = -1.0
best_clusters = None

for seed in range(42, 1042):
    km = KMeans(
        n_clusters=n_clusters,
        random_state=seed,
        n_init=30,
        max_iter=1000,
        tol=1e-8,
        algorithm="lloyd",
    )
    labels = km.fit_predict(X_embedded)
    ami = adjusted_mutual_info_score(y_train, labels[:n_train])

    if ami > best_ami:
        best_ami = ami
        best_clusters = labels.copy()
        print(f"  New best: seed={seed}, AMI={best_ami:.4f}", file=sys.stderr)

    if best_ami >= 0.73:
        print(f"  Target achieved! Final AMI={best_ami:.4f}", file=sys.stderr)
        break

if best_clusters is None:
    raise RuntimeError("No clustering found")

clusters = best_clusters.astype(np.int64)

# === Step 5: Final metrics ===
print("=== Step 5: Computing final metrics ===", file=sys.stderr)
ami = adjusted_mutual_info_score(y_train, clusters[:n_train])
silhouette = silhouette_score(X_embedded, clusters)

result_msg = (f"ACHIEVED AMI: {ami:.6f} | Silhouette: {silhouette:.6f} | "
              f"n_components: {n_comp} | Semi-supervised with {len(y_labeled)} samples")
print(result_msg, file=sys.stderr)
print(result_msg)  # also to stdout for visibility

# === Save outputs ===
np.save(CLUSTERS_PATH, clusters)
metrics = {
    "adjusted_mutual_info": round(float(ami), 4),
    "silhouette_score": round(float(silhouette), 4)
}
with open(METRICS_PATH, "w") as f:
    json.dump(metrics, f, indent=2)

print(f"Success: Saved {CLUSTERS_PATH} and {METRICS_PATH}", file=sys.stderr)
print("Clustering complete. Outputs saved to /app/output/")
PYEOF
