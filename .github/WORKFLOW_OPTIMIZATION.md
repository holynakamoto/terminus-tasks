# GitHub Actions CI/CD Optimization Summary

## Changes Implemented

The task validation workflow has been significantly optimized to reduce execution time and cost, particularly for PR feedback cycles.

### 1. **Split Difficulty Validation into Parallel Jobs** ⭐ Biggest Impact

**Before:** GPT-5 and Claude ran sequentially in one job with 180-minute timeout
```yaml
validate-difficulty:
  - Run GPT-5 (3 iterations × ~10-15 min = ~45 min)
  - Run Claude (3 iterations × ~10-15 min = ~45 min)
  Total: ~90+ minutes sequential
```

**After:** Three separate jobs running in parallel
```yaml
validate-difficulty-gpt:       # Runs in parallel
validate-difficulty-claude:    # Runs in parallel
validate-difficulty-summary:   # Merges results
```

**Impact:** ~50% faster on difficulty evaluation stage (90min → ~45min)

### 2. **Conditional Execution by Branch** ⭐ Major Impact

Difficulty evaluations now **only run on main branch** or when explicitly requested via `workflow_dispatch`.

```yaml
if: |
  needs.detect-changed-tasks.outputs.has_tasks == 'true'
  && (github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch')
```

**Impact for PRs:**
- **Before:** Static checks + Oracle + NOP + Difficulty = ~2.5+ hours
- **After:** Static checks + Oracle + NOP only = ~30-45 minutes
- **Speedup:** ~75% faster PR feedback cycle

### 3. **Dynamic Run Count Based on Event Type**

```bash
if [ "${{ github.event_name }}" = "pull_request" ]; then
  RUN_COUNT=1  # Quick feedback
else
  RUN_COUNT=3  # Thorough validation on main
fi
```

**Impact:** 
- PRs: 1 run per model (if difficulty is manually triggered)
- Main: 3 runs per model for statistical confidence
- Potential additional 66% speedup when needed

### 4. **Aggressive UV Package Caching**

Added dedicated caching for UV package manager:

```yaml
- name: Cache uv packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-harbor-0.1.25-terminal-bench-0.2.18
    restore-keys: |
      ${{ runner.os }}-uv-
```

**Impact:** 
- Saves ~30-60 seconds per difficulty job
- Reduces network bandwidth and installation overhead

### 5. **Reduced Timeout for Parallel Jobs**

- **Before:** Single job with 180-minute timeout
- **After:** Two parallel jobs with 90-minute timeouts each

**Impact:** Better resource utilization, earlier failure detection

## Performance Summary

### PR Workflow (Most Common)
| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Static Checks | ~5 min | ~5 min | No change |
| Oracle Validation | ~15 min | ~15 min | No change |
| NOP Validation | ~5 min | ~5 min | No change |
| Difficulty Eval | ~90 min | **SKIPPED** | ✅ ~90 min saved |
| **Total** | **~115 min** | **~30 min** | **~74% faster** |

### Main Branch (Post-Merge)
| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| Static Checks | ~5 min | ~5 min | No change |
| Oracle Validation | ~15 min | ~15 min | No change |
| NOP Validation | ~5 min | ~5 min | No change |
| Difficulty Eval | ~90 min sequential | **~45 min parallel** | **✅ 50% faster** |
| **Total** | **~115 min** | **~70 min** | **~39% faster** |

## Additional Recommendations Not Yet Implemented

### Quick Wins (Low Effort, Medium Impact)
1. **Shared Docker cache** across tasks (if Dockerfiles are similar)
2. **Pre-build common Docker images** and push to GHCR
3. **Add `timeout-minutes` to individual harbor runs** (not just job-level)

### Medium Effort (High Impact)
1. **Use faster models for PRs** (e.g., GPT-4o-mini instead of GPT-5)
   ```yaml
   if: github.event_name == 'pull_request'
   then: model = "gpt-4o-mini"
   else: model = "gpt-5"
   ```
2. **Self-hosted runners** on beefy machines (2-5× faster for heavy workloads)
3. **BuildJet or similar** third-party runners (faster + cheaper)

### Future Optimizations
1. **Larger GitHub runners** (8-core instead of 2-core) if on Team/Enterprise plan
2. **Skip NOP validation** on trivial changes (e.g., documentation-only PRs)
3. **Incremental Docker builds** with better layer caching strategies

## How to Test

1. **Test PR workflow** (no difficulty evaluation):
   ```bash
   git checkout -b test-optimization
   # Make a small change to a task
   git add . && git commit -m "test: optimize workflow"
   git push origin test-optimization
   # Create PR and observe ~30 min total time
   ```

2. **Test main branch workflow** (with parallel difficulty):
   ```bash
   # Merge PR to main
   # Observe ~70 min total time with parallel GPT/Claude
   ```

3. **Manually trigger difficulty on PR** (optional):
   - Go to Actions → Task Validation → Run workflow
   - Select your PR branch
   - Choose "all" test type
   - This will run 1 iteration per model

## Cost Impact

**Assumptions:**
- GitHub Actions pricing: ~$0.008/min for Linux runners
- Before optimization: 115 min/PR × 10 PRs/day = 1,150 min/day
- After optimization: 30 min/PR × 10 PRs/day = 300 min/day

**Savings:**
- **850 minutes/day** = ~$6.80/day = ~$204/month saved on PR runs
- Full validation still runs on main branch (unchanged cost)

## Summary

✅ **Implemented optimizations provide:**
- **74% faster PR feedback** (115 min → 30 min)
- **39% faster main branch validation** (115 min → 70 min)
- **~$200/month cost savings** on compute
- **Better resource utilization** through parallel execution
- **Maintained validation quality** (3 runs per model on main branch)

The workflow now provides rapid PR feedback while maintaining thorough validation on the main branch.
