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
# Dataset: 500 samples (250 labeled + 250 unlabeled), 8 classes, 40 features
# This MUST match the dataset generated in test.sh
RUN python3 <<'EOF'
import numpy as np
from sklearn.datasets import make_classification
import os

# Generate challenging dataset with moderate separation (calibrated for AMI > 0.72-0.78)
# Oracle should achieve ~0.73-0.76, threshold set to 0.72 for Medium difficulty
# Increased complexity: more features, more noise, lower separation, more unlabeled data

# Make sure these values match what tests expect
n_samples_train = 250  # Training samples with labels (reduced from 300)
n_samples_unlabeled = 250  # Unlabeled samples (increased from 100 to 250)
n_samples = n_samples_train + n_samples_unlabeled  # 500 total

X, y = make_classification(
    n_samples=n_samples,
    n_features=40,  # Increased from 25 to 40
    n_classes=8,
    n_informative=20,  # Increased informative features
    n_redundant=10,  # Increased redundant features
    n_repeated=5,  # Add repeated (duplicated) features
    n_clusters_per_class=1,
    class_sep=1.15,  # Lower separation - makes clustering harder (was 1.8)
    flip_y=0.05,  # Add 5% label noise for realism (was 0.00)
    random_state=42
)

# Split: first 250 samples are labeled training data, all 500 are in X_full
X_train = X[:n_samples_train]
y_train = y[:n_samples_train]
X_full = X  # Full dataset (250 labeled + 250 unlabeled)
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