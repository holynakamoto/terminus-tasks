# Supervised Clustering with Representation Learning

## Task Description

Given a partially labeled dataset, develop a clustering approach that uses the available label information to discover meaningful cluster structure. Learn a feature transformation from the labeled examples that captures class structure, then apply clustering in the transformed space.

## Input

A dataset file at `/app/data/dataset.npz` containing:
- `X_train`: Feature vectors for samples with known class labels
- `y_train`: Class labels for the training samples  
- `X_full`: Complete feature matrix (includes both labeled and unlabeled samples)
- `n_clusters`: Target number of clusters to identify

## Expected Output

Two files in `/app/output/`:

1. **`clusters.npy`**: Integer array of cluster assignments (0 to n_clusters-1) for all samples in X_full

2. **`metrics.json`**: JSON object with:
   - `adjusted_mutual_info`: Agreement between training labels and cluster assignments (computed on labeled subset only)
   - `silhouette_score`: Quality measure computed on the transformed full dataset

## Approach

1. **Dimensionality Reduction with Supervision**
   - Apply Neighborhood Components Analysis (NCA) from scikit-learn to learn a supervised transformation
   - **You must select `n_components` through validation** (e.g., cross-validation or hold-out validation using silhouette score or AMI on labeled validation data)
   - Do not use default parameters. You must demonstrate thoughtful hyperparameter selection:
     - Choose `n_components` that balances dimensionality reduction with information preservation
     - Consider tuning `max_iter` and other NCA parameters to ensure convergence
     - Use validation evidence (not heuristics like `n_components = n_classes`) to justify your choice
   - Ensure reproducibility by using a fixed random seed

2. **Clustering**
   - Apply K-means clustering from scikit-learn to the NCA-transformed features (not raw features)
   - Use the target number of clusters provided in the dataset
   - **You must use multiple initializations** (`n_init` ≥ 20) and select the best run based on inertia or silhouette score
   - Use stable initialization parameters (fixed `random_state`) to ensure consistent results

3. **Quality Requirements**
   - The clustering must achieve strong alignment with ground-truth class structure
   - **Adjusted Mutual Information (AMI) between true labels and clusters must be > 0.68**
   - This requires optimal or near-optimal selection of NCA `n_components` and proper NCA/KMeans tuning
   - Note: AMI > 0.68 indicates strong recovery of the true cluster structure, requiring careful parameter selection, validation, and multiple initialization trials

4. **Clustering Requirements**
   - Verify that all samples receive valid cluster IDs in the range [0, n_clusters-1)
   - The clustering should produce exactly n_clusters distinct clusters
   - **Cluster coherence**: Unlabeled samples should cluster with nearby labeled samples. At least 40% of unlabeled samples must share the same cluster ID as their nearest labeled neighbor in the raw feature space. This ensures the clustering approach genuinely uses the feature space structure rather than arbitrary assignments.

5. **Metric Computation**
   - Adjusted Mutual Information: Compare training labels (y_train) with cluster assignments for the corresponding samples (first len(X_train) elements). Valid range: [-1, 1]
   - **Silhouette Score: Must be computed on the NCA-transformed (low-dimensional) features, not the raw input features**. Valid range: [-1, 1]
   - Round both metrics to exactly 4 decimal places

## Requirements

- Training samples correspond to the first `len(X_train)` rows of `X_full`
- Outputs must be deterministic and reproducible (use fixed random seeds)
- Create `/app/output/` directory if it doesn't exist
- All cluster IDs must be integers in [0, n_clusters-1)
- You must use `NeighborhoodComponentsAnalysis` and `KMeans` from scikit-learn
- You may not rely on default parameters for critical hyperparameters (`n_components` in NCA, `n_init` in KMeans)
- You must demonstrate parameter selection through validation, not simple heuristics
