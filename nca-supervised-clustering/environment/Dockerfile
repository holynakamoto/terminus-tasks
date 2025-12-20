FROM ubuntu:24.04

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install pinned dependencies (exact versions for reproducibility)
RUN pip3 install --break-system-packages --no-cache-dir \
    "numpy==1.26.4" \
    "scikit-learn==1.3.2"

# Generate test dataset so it's available when Oracle agent runs
# Dataset: 400 samples (300 labeled + 100 unlabeled), 8 classes, 25 features
RUN python3 <<'EOF'
import numpy as np
from sklearn.datasets import make_classification
import os

# Generate challenging dataset with good separation (calibrated for AMI > 0.65-0.80)
n_samples_train = 300  # Training samples with labels
n_samples_unlabeled = 100  # Unlabeled samples
n_samples = n_samples_train + n_samples_unlabeled  # 400 total

X, y = make_classification(
    n_samples=n_samples,
    n_features=25,
    n_classes=8,
    n_informative=18,
    n_redundant=4,
    n_clusters_per_class=1,
    class_sep=1.8,  # Higher separation - makes clustering more achievable with good tuning
    flip_y=0.00,  # No label noise - cleaner separation
    random_state=42
)

# Split: first 300 samples are labeled training data, all 400 are in X_full
X_train = X[:n_samples_train]
y_train = y[:n_samples_train]
X_full = X  # Full dataset (300 labeled + 100 unlabeled)
n_clusters = 8

os.makedirs('/app/data', exist_ok=True)
np.savez(
    '/app/data/dataset.npz',
    X_train=X_train,
    y_train=y_train,
    X_full=X_full,
    n_clusters=np.array(n_clusters)
)
EOF

WORKDIR /app