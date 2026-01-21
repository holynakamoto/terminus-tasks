# CI/CD Pipeline Timing Baseline Analysis
**Run ID:** 21221400627  
**Date:** 2026-01-21  
**Total Duration:** 11 minutes 26 seconds (11.43 min)  
**Status:** ✅ SUCCESS

## Detailed Breakdown (1 run per model)

| Stage | Duration | % of Total | Status | Notes |
|-------|----------|------------|--------|-------|
| **detect-changed-tasks** | 0.05 min (3s) | 0.4% | ✅ | Negligible |
| **static-checks** | 3.01 min (181s) | 26.3% | ✅ | Ruff + LLMaJ |
| **validate-oracle** | 0.73 min (44s) | 6.4% | ✅ | Oracle solution test |
| **validate-nop** | 0.48 min (29s) | 4.2% | ✅ | NOP test (parallel) |
| **validate-difficulty-claude** | 3.55 min (213s) | 31.1% | ✅ | 1 Claude run |
| **validate-difficulty-gpt** | 7.20 min (432s) | 63.0% | ✅ | 1 GPT-5 run |
| **validate-difficulty-summary** | 0.13 min (8s) | 1.1% | ✅ | Merge results |
| **summary** | 0.03 min (2s) | 0.3% | ✅ | Final summary |
| | | | |
| **TOTAL (wall clock)** | **11.43 min** | **100%** | ✅ | End-to-end |

## Critical Path Analysis

Since jobs run in parallel, the **critical path** is:
1. detect-changed-tasks: 0.05 min
2. static-checks: 3.01 min (parallel with oracle/nop doesn't matter)
3. oracle OR nop (whichever is longer): 0.73 min
4. **difficulty-gpt**: 7.20 min (runs parallel with Claude but GPT is slower)
5. difficulty-summary: 0.13 min
6. summary: 0.03 min

**Critical Path Total:** 0.05 + 3.01 + 0.73 + 7.20 + 0.13 + 0.03 = **11.15 min**

## Key Findings

### 🔴 Problem 1: GPT-5 is 2× slower than Claude
- **Claude:** 3.55 min (213s)
- **GPT-5:** 7.20 min (432s)
- **Ratio:** 2.03× slower

**Why?**
- GPT-5 API has higher latency
- Possibly different token generation speeds
- Could be infrastructure/routing to OpenAI via Portkey

### 🎯 Bottleneck: GPT-5 Difficulty Evaluation
GPT-5 alone accounts for **63%** of the critical path time (7.2 / 11.43 = 63%).

## Target: Under 25 Minutes

**Current:** 11.43 min ✅ Already under 25 min!

But the user wants to optimize further. Let's see what we can target:

### Scenario 1: Current (1 run per model)
- **Current total:** 11.43 min
- **Already 54% under target!**

### Scenario 2: If we go to 2 runs per model
- Claude: 3.55 × 2 = 7.10 min
- GPT-5: 7.20 × 2 = 14.40 min
- Critical path: 0.05 + 3.01 + 0.73 + 14.40 + 0.13 + 0.03 = **18.35 min**
- **Still under 25 min!** ✅

### Scenario 3: If we go to 3 runs per model
- Claude: 3.55 × 3 = 10.65 min
- GPT-5: 7.20 × 3 = 21.60 min
- Critical path: 0.05 + 3.01 + 0.73 + 21.60 + 0.13 + 0.03 = **25.55 min**
- **Over 25 min!** ❌

### Scenario 4: Maximum runs to stay under 25 min
We have 25 - (0.05 + 3.01 + 0.73 + 0.13 + 0.03) = **21.05 min** for difficulty eval.

Max GPT-5 runs: 21.05 / 7.20 = **2.92 runs**

**Answer: We can do 2 runs per model and stay under 25 min.**

## Optimization Opportunities

### 1. Skip GPT-5 entirely (most aggressive)
- Run only Claude for difficulty
- **Saves:** 7.20 min
- **New total:** 4.23 min (!!)
- **Trade-off:** Less model diversity

### 2. Reduce static-checks time (3.01 min → ~1.5 min)
**How:**
- Cache uv packages better
- Skip LLMaJ on non-code changes
- Run Ruff in parallel with LLMaJ as separate jobs

**Potential:** Save ~1.5 min

### 3. Pre-built Docker images (not yet active)
- Oracle: 0.73 min → ~0.30 min
- NOP: 0.48 min → ~0.20 min
- **Saves:** ~0.70 min

### 4. Use faster GPT model for PRs
- Use GPT-4o or GPT-4o-mini instead of GPT-5 for PR validation
- Reserve GPT-5 for main branch only
- GPT-4o is likely 2-3× faster

## Recommended Configuration

### For PR (fast feedback):
```yaml
if PR:
  - Static checks: ~3 min
  - Oracle/NOP: ~1 min
  - Difficulty: SKIP (or 1 run of GPT-4o-mini only)
  - Total: ~4-5 min
```

### For Main Branch (thorough):
```yaml
if Main:
  - Static checks: ~3 min
  - Oracle/NOP: ~1 min
  - Difficulty: 2 runs × (Claude 3.55 min + GPT-5 7.20 min parallel)
  - Total: ~18 min (well under 25 min)
```

## Next Steps

1. ✅ **Current state is good** - 11.43 min is excellent!
2. **Enable pre-built Docker images** - saves another ~0.7 min
3. **Consider 2 runs per model** for better statistical confidence (staying at 18 min)
4. **For sub-5-min PRs**: Skip difficulty entirely (already configured)

## Cost Analysis

**Current (1 run per model on main):**
- 11.43 min × $0.008/min = **$0.091 per run**
- 10 merges/day = **$0.91/day** = **~$27/month**

**If 2 runs per model:**
- 18.35 min × $0.008/min = **$0.147 per run**
- 10 merges/day = **$1.47/day** = **~$44/month**

Still very affordable!
