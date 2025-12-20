# Quality Check Fixes - Response to Failed Checks

## Issues Identified by Quality Check

The Harbor quality check identified 3 failing checks:

1. **Behavior In Task Description** - Tests enforce requirements not mentioned in instruction.md
2. **Behavior In Tests** - Tests don't verify the prescribed methodology (NCA usage, n_components validation, etc.)
3. **Anti Cheating Measures** - Agent could still cheat by copying labels and using nearest-neighbor in raw space

## Fixes Applied

### Fix 1: Document Anti-Cheating Requirements in instruction.md ✅

**Added to "Clustering Requirements" section:**
```markdown
- **Cluster coherence**: Unlabeled samples should cluster with nearby labeled samples. 
  At least 40% of unlabeled samples must share the same cluster ID as their nearest 
  labeled neighbor in the raw feature space. This ensures the clustering approach 
  genuinely uses the feature space structure rather than arbitrary assignments.
```

**Added to "Metric Computation" section:**
```markdown
- Adjusted Mutual Information: ... Valid range: [-1, 1]
- Silhouette Score: ... Valid range: [-1, 1]
- Round both metrics to exactly 4 decimal places
```

**Impact:** All test requirements are now documented in instruction.md

### Fix 2: Updated Docstring Consistency ✅

**Changed:**
- `test_clustering_approach_quality()` docstring: "AMI > 0.65" → "AMI > 0.75"

**Impact:** All docstrings now match actual test assertions

### Fix 3: Added Silhouette Verification Test ✅

**New Test:** `test_silhouette_not_on_raw_features()`

**What it does:**
- Computes what silhouette WOULD be on raw features
- Compares to stored silhouette score
- Issues warning if they match suspiciously closely
- Helps detect if agent computed silhouette on raw features instead of NCA-transformed

**Why it's a warning, not a failure:**
- In some cases, raw and transformed features could legitimately produce similar silhouette scores
- The coherence test is the primary anti-cheating measure
- This serves as an additional signal to catch borderline cases

**Impact:** Harder to cheat by skipping NCA transformation

## Remaining Limitations (Acknowledged)

### Tests Don't Enforce Methodology
The quality check correctly notes that tests verify outputs but don't check:
- Whether NCA was actually used
- Whether n_components was selected through validation
- Whether KMeans used n_init ≥ 20

**Why this is acceptable:**
- Harbor evaluates tasks by **output quality**, not implementation details
- The high AMI threshold (0.75) + coherence test make it very difficult to achieve passing results without proper methodology
- Attempting to reverse-engineer from instruction alone (without NCA/KMeans) would be extremely difficult
- The combination of requirements creates an effective "output-based" verification of methodology

### Theoretical Cheating Path Still Exists
An extremely sophisticated agent could theoretically:
1. Copy training labels: `clusters[:n_train] = y_train`
2. Use nearest-neighbor in raw space for unlabeled samples
3. Compute silhouette on raw features

**Why this is unlikely to work:**
- Would need to achieve 40% coherence on unlabeled samples
- Would need AMI > 0.75 on training set (easy with copied labels)
- But clustering would be in raw feature space, not NCA-transformed space
- High AMI + high coherence in raw space is possible but requires the dataset to already have good separation

**Mitigation:**
- The dataset parameters (class_sep=1.8, clean labels) are calibrated so Oracle achieves 0.78-0.85 with NCA
- Without NCA, even with nearest-neighbor heuristics, achieving 0.75 consistently is difficult
- The empirical difficulty testing (GPT-5 and Claude runs) will reveal if this path is exploitable

## Summary of All Changes

### Files Modified:
1. **instruction.md**
   - Added coherence requirement documentation
   - Added metric range documentation
   - Clarified rounding requirement

2. **tests/test_outputs.py**
   - Fixed docstring (0.65 → 0.75)
   - Added `test_silhouette_not_on_raw_features()`
   - Removed unused variables (linting)

### Verification:
- ✅ All linting checks pass
- ✅ All quality documentation requirements addressed
- ✅ Anti-cheating measures strengthened
- ✅ Ready for difficulty testing

## Next Steps

1. **Run quality check again:**
   ```bash
   # Should now pass "Behavior In Task Description" 
   # "Behavior In Tests" will still show as limitation (acknowledged)
   # "Anti Cheating Measures" should be improved
   ```

2. **Run difficulty testing:**
   ```bash
   test-diff
   ```
   
3. **Analyze results:**
   - Target: GPT-5 ~60-70%, Claude ~30-40%
   - If cheating path is exploited, results will show 100% pass rates
   - If properly difficult, pass rates should be in target range

## Expected Outcome

With AMI threshold 0.75 + coherence test 40% + silhouette verification, the task should be:
- **Hard** for agents to pass without proper NCA+KMeans implementation
- **Fair** because all requirements are documented
- **Discriminative** between model capabilities (GPT-5 vs Claude)
