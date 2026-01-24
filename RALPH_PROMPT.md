# Ralph Loop Task: Validate cracked256 Task for Snorkel Submission

## Objective
Validate that the cracked256 password cracking task is fully ready for Snorkel/Harbor evaluation with 100% Oracle success rate.

## Success Criteria

### 1. Pre-Generated Data Files ✓
- [x] `tasks/cracked256/environment/hashes.txt` exists (13 lines: 10 valid + 3 malformed)
- [x] `tasks/cracked256/environment/dictionary.txt` exists (12 base words)
- [x] Data is deterministic (generated with `random.seed(42)`)
- [x] Specific hash verification: user001 hash matches expected value

### 2. Oracle Solution ✓
- [x] `tasks/cracked256/solution/solve.sh` has conditional data generation
- [x] Skips generation if files exist (Snorkel mode)
- [x] Enhanced mangling rules include:
  - [x] Partial leet + symbol (no number): `P@ssw0rd!`, `T3st@`
  - [x] Partial leet maps for subset substitutions
  - [x] Full leet + number + symbol combos
- [x] Oracle achieves 10/10 (100%) with pre-generated data
- [x] Execution completes in < 30 seconds

### 3. Snorkel Compliance ✓
- [x] `tasks/cracked256/environment/Dockerfile.snorkel-v2` exists
- [x] Dockerfile uses pre-generated data files (no build-time execution)
- [x] Docker build completes in < 10 seconds
- [x] No privileged mode required
- [x] Base image: `python:3.11-slim` (not overly specific)

### 4. Test Suite ✓
- [x] `tasks/cracked256/tests/test_outputs.py` validates:
  - [x] Output file exists and has content
  - [x] Canary string present (anti-cheating)
  - [x] CSV format valid with header
  - [x] Passwords sorted alphabetically
  - [x] All cracked passwords are cryptographically valid
  - [x] Hash file integrity (10 valid, 3 malformed)
  - [x] Mangling rules applied (30%+ crack rate required)
  - [x] Comprehensive transformations (40%+ combined patterns)

### 5. Submission Package ✓
- [x] `prepare-snorkel-submission-v2.sh` creates valid package
- [x] Package includes:
  - [x] Dockerfile (Snorkel-compliant)
  - [x] hashes.txt and dictionary.txt (pre-generated)
  - [x] solution/solve.sh (fixed Oracle)
  - [x] tests/test_outputs.py and test.sh
  - [x] task.toml (with timeouts)
- [x] Package size reasonable (< 20KB)
- [x] No forbidden files (generate_data.py excluded for Snorkel)

### 6. CI Integration ✓
- [x] `.github/workflows/task-validation.yml` fixed:
  - [x] Artifact downloads conditional on job success
  - [x] No errors for skipped difficulty evaluations
- [x] GitHub Actions still work with original Dockerfile
- [x] Backward compatible (no breaking changes)

### 7. Documentation ✓
- [x] `SNORKEL_DOCKERFILE_FIX.md` explains architectural changes
- [x] `SNORKEL_SUPPORT_TICKET.md` documents debugging process
- [x] `PR_DESCRIPTION.md` comprehensive with all changes
- [x] Code comments explain conditional logic

## Verification Commands

Run these commands in order. All must pass:

```bash
# 1. Verify pre-generated data
test -f tasks/cracked256/environment/hashes.txt && echo "✓ hashes.txt exists"
test $(wc -l < tasks/cracked256/environment/hashes.txt) -eq 13 && echo "✓ 13 lines"
test -f tasks/cracked256/environment/dictionary.txt && echo "✓ dictionary.txt exists"

# 2. Run Oracle test locally
bash test-oracle-local.sh | grep "100%" && echo "✓ Oracle achieves 100%"

# 3. Validate Snorkel package
bash prepare-snorkel-submission-v2.sh && echo "✓ Package created"
test -f ~/cracked256-snorkel-submission-v2.zip && echo "✓ ZIP exists"

# 4. Check git status
git status --porcelain | wc -l | grep -q "^0$" && echo "✓ Clean working tree"

# 5. Verify PR branch
git branch --show-current | grep "claude/fix-cracked256-difficulty" && echo "✓ On PR branch"
git log --oneline -1 | grep -q "PR description" && echo "✓ Latest commit ready"
```

## Completion Signal

When ALL criteria above are met (all checkboxes checked, all verification commands pass), output exactly:

```
RALPH_VALIDATION_COMPLETE

All cracked256 task validation passed:
- Oracle: 100% success with pre-generated data
- Snorkel: Compliant Dockerfile and package
- CI: Fixed artifact downloads
- Tests: All passing
- Documentation: Complete

Task is ready for Snorkel submission and PR merge.

DONE
```

## Iteration Instructions

If any criteria fail:
1. Identify the specific failure
2. Fix the issue
3. Re-run verification commands
4. Update this document's checkboxes
5. Commit changes: `git commit -m "Ralph iteration: Fix [issue]"`
6. Continue loop

After 3 consecutive failures on the same criterion, document the blocker in `RALPH_BLOCKERS.md` and escalate.

## Current Status

✅ **ALL CRITERIA MET** - Task validation complete!

Ready to output completion signal.
