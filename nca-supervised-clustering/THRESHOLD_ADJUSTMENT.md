# AMI Threshold Adjustment - Critical Fix

## Problem Discovered

After initial fixes raised the threshold to 0.75, Oracle testing revealed:
```
ACHIEVED AMI: 0.695337 | Silhouette: 0.192226 | n_components: 7
```

**The Oracle solution failed its own test!** AMI of 0.695 < 0.75 threshold.

## Root Cause

The threshold of 0.75 was set based on an **assumption** that the Oracle would achieve 0.78-0.85, but actual testing showed it only achieves ~0.69-0.70. This made the task **impossible** even for the reference solution.

## Fix Applied

**Lowered AMI threshold: 0.75 → 0.68**

### Rationale:
- Oracle achieves: ~0.695 AMI
- New threshold: 0.68
- Buffer: 0.015 above threshold (small but achievable)
- Still challenging: Requires good n_components selection and KMeans initialization

### Files Updated:
1. **tests/test_outputs.py**
   - Threshold assertions: 0.75 → 0.68
   - Comments: "oracle achieves ~0.78-0.85" → "oracle achieves ~0.69-0.72"
   - Docstring: "AMI > 0.75" → "AMI > 0.68"

2. **instruction.md**
   - Quality requirement: 0.75 → 0.68
   - Description adjusted accordingly

3. **tests/test.sh**
   - Calibration comments: 0.75-0.85 → 0.68-0.72

## Expected Difficulty

With AMI threshold at 0.68:
- **Oracle**: Should pass (achieves 0.695)
- **GPT-5**: May achieve 60-80% (needs good tuning to reach 0.68)
- **Claude Sonnet**: May achieve 30-50% (harder but achievable)
- **Target**: Medium-Hard difficulty

The 0.68 threshold is still significantly higher than the original 0.65, which both models passed at 100%. This should maintain difficulty while being achievable.

## Verification Steps

1. **Oracle Test** (next step):
   ```bash
   test-oracle
   ```
   Expected: Oracle passes with AMI ~0.695

2. **Full Difficulty Test**:
   ```bash
   test-diff
   ```
   Expected: Pass rates in 40-70% range

## Comparison

| Threshold | Oracle | Expected GPT-5 | Expected Claude | Difficulty | Status |
|-----------|--------|----------------|-----------------|------------|--------|
| 0.65 (original) | 100% pass | 100% | 100% | TRIVIAL | ❌ Rejected |
| 0.75 (first fix) | 0% pass (0.695) | N/A | N/A | IMPOSSIBLE | ❌ Broken |
| 0.68 (current) | ~100% pass (0.695) | 60-80% | 30-50% | MEDIUM-HARD | ✅ Expected |

## Notes

- The dataset parameters (class_sep=1.8, no noise) limit how high AMI can go
- To achieve higher Oracle AMI would require either:
  1. Better dataset separability (increase class_sep)
  2. More sophisticated Oracle solution
  3. Different dataset generation approach

- Current approach prioritizes **realistic difficulty** over theoretical perfection
- The coherence test (40%) remains as primary anti-cheating measure
