# Supervised Clustering with NCA Embedding

## Task Summary

You are given a partially labeled dataset. Your job is to:

1. **Learn a supervised embedding** using scikit-learn’s **Neighborhood Components Analysis (NCA)** on the **labeled** data.
2. **Transform the full dataset** into that embedding.
3. **Cluster the full embedded dataset** using **KMeans**.
4. **Write outputs** (`clusters.npy`, `embedding.npy`, `metrics.json`) to `/app/output/`.
5. **Evaluate clustering quality** using:
   - **Adjusted Mutual Information (AMI)** on the labeled subset only
   - **Silhouette score** on the embedded full dataset

This task is about implementing the pipeline correctly and reproducibly (not about hitting a specific AMI threshold).

## Input

A dataset file at:

- `/app/data/dataset.npz`

It contains:

- `X_train`: feature matrix for labeled samples (shape `(n_train, n_features)`)
- `y_train`: integer class labels for `X_train` (shape `(n_train,)`)
- `X_full`: full feature matrix containing both labeled and unlabeled samples (shape `(n_total, n_features)`)
- `n_clusters`: target number of clusters (scalar)

**Important:** The labeled samples correspond to the first `len(X_train)` rows of `X_full`.

## Required Output Files (in `/app/output/`)

### 1) `clusters.npy`
- A 1D integer NumPy array of shape `(len(X_full),)`
- Each entry is a cluster ID in `[0, n_clusters - 1]`
- Must contain **exactly `n_clusters` distinct** cluster IDs overall

### 2) `embedding.npy`
- A 2D float NumPy array of shape `(len(X_full), n_components)`
- This must be the **NCA-transformed embedding of `X_full`** (i.e., `embedding = nca.transform(X_full_preprocessed)`)
- Must be finite (no NaN/inf)
- Must have `n_components >= 2` so silhouette is meaningful

### 3) `metrics.json`
A JSON object containing exactly these keys:

- `adjusted_mutual_info`: AMI between `y_train` and `clusters[:len(X_train)]`
- `silhouette_score`: silhouette score computed as `silhouette_score(embedding, clusters)`

Both values must:
- be numeric (int/float)
- be in the range `[-1, 1]`
- be rounded to **exactly 4 decimal places**

## Required Algorithms

You must use:

- `sklearn.neighbors.NeighborhoodComponentsAnalysis` for the embedding
- `sklearn.cluster.KMeans` for clustering

## Required Computation Details

### NCA training
- Fit NCA using **only** the labeled data: `(X_train, y_train)`
- Then use the fitted NCA model to transform:
  - the labeled data (if needed)
  - the full dataset `X_full` to produce `embedding.npy`

### KMeans clustering
- Run KMeans on the **embedded** full dataset (`embedding.npy`), not on raw `X_full`.
- Use `n_clusters` from the dataset file.
- Ensure outputs are deterministic/reproducible:
  - Use a fixed `random_state`
  - Use a non-trivial `n_init` (recommended: `>= 20`)

### Metric computation
- **AMI:** compute only on the labeled subset:
  - `adjusted_mutual_info_score(y_train, clusters[:len(X_train)])`
- **Silhouette:** compute only on the embedding:
  - `silhouette_score(embedding, clusters)`
- Round both to exactly 4 decimals before writing `metrics.json`.

## Determinism

Your outputs must be reproducible. Use fixed random seeds (e.g., `random_state=0`) and deterministic preprocessing.

## Notes / Tips (non-mandatory)

- Standardizing features (e.g., `StandardScaler`) often helps NCA/KMeans stability.
- Be careful to keep array alignment correct: the first `len(X_train)` entries of `clusters.npy` correspond to the labeled samples in `y_train`.
