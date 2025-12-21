#!/bin/bash
set -euo pipefail

# Ensure reward file is created even on early exit
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

# Install dependencies
apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
source $HOME/.local/bin/env

pip3 install --break-system-packages --no-cache-dir \
    "numpy==1.26.4" \
    "scikit-learn==1.3.2" \
    "pytest==8.4.1" \
    "pytest-json-ctrf==0.3.5"

# Generate test dataset (needed for Oracle agent to run solution)
echo "Generating test dataset..."
python3 <<'EOF'
import numpy as np
from sklearn.datasets import make_classification
import os

# Generate challenging dataset with good separation (calibrated for AMI > 0.70-0.75)
# Oracle should achieve ~0.70-0.72, threshold set to 0.70 for Medium-Hard difficulty

# Make sure these values match what tests expect
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
print("✓ Test dataset created at /app/data/dataset.npz")
EOF

# Note: The Oracle agent runs the solution automatically before test.sh executes
# We just need to ensure the dataset exists and then run the tests

# Run tests
echo "Running tests..."
if python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
  echo "✓ All tests passed"
  echo 1 > /logs/verifier/reward.txt
else
  echo "✗ Tests failed"
  echo 0 > /logs/verifier/reward.txt
fi
