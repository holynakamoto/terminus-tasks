# Fix cracked256 task for Snorkel/Harbor evaluation

## Summary

Fixes critical issues preventing `cracked256` task from passing Snorkel/Harbor evaluation. The Oracle (reference solution) was achieving only 60% success (0.0 reward) due to architectural mismatch between pre-generated data and runtime behavior.

## Problems Identified

### 1. CI Artifact Download Errors
- Difficulty evaluation jobs only run on `main` branch
- Summary job was unconditionally trying to download artifacts
- **Fix**: Made artifact downloads conditional on upstream job success

### 2. Snorkel Docker Build Failures
- Original Dockerfile executed Python at build time (2-3 min builds)
- Violated Snorkel's "lightweight and reproducible" requirements
- Caused CodeBuild timeouts and NoSuchKey errors (10/13 builds failed)
- **Fix**: Pre-generated deterministic data files, Docker builds now < 5 seconds

### 3. Oracle Solution Mismatch (CRITICAL)
- Oracle was **overwriting** pre-generated `hashes.txt` with NEW random data
- Then trying to crack the NEW data with incomplete mangling rules
- Result: Only 60% success → 0.0 reward (needs 100% for pass)
- **Fix**: Conditional data generation + enhanced password mangling rules

## Changes

### Oracle Solution Fixes (`tasks/cracked256/solution/solve.sh`)

**1. Conditional Data Generation**
```bash
# Skip generation if files already exist (Snorkel pre-generates them)
if [ -f /app/hashes.txt ] && [ -f /app/dictionary.txt ]; then
    echo "[DEBUG] Pre-generated data files detected (Snorkel mode)"
else
    # Generate at runtime (GitHub Actions mode)
    python3 << 'GENERATE_DATA'
    ...
fi
```

**2. Enhanced Mangling Rules**

Fixed two missing patterns:

**Pattern 1: Partial Leet + Symbol (No Number)**
- ❌ Was missing: `P@ssw0rd!`, `T3st@`
- ✅ Now generates: `partial_leet_cap + symbol`

**Pattern 2: Partial Leet Transformations**
- ❌ Was applying ALL leet rules: `P@$$w0rd!` (wrong)
- ✅ Now applies subsets: `P@ssw0rd!` (correct)
- Added 5 partial leet maps for common substitution patterns

**Validation**: All 10 target passwords now successfully cracked (100%)

### Snorkel Compliance (`tasks/cracked256/environment/`)

**Pre-generated Data Files**
- `hashes.txt` - 13 lines (10 valid + 3 malformed)
- `dictionary.txt` - 12 base words
- Generated with `random.seed(42)` for determinism

**Snorkel-Compliant Dockerfile** (`Dockerfile.snorkel-v2`)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY hashes.txt /app/hashes.txt
COPY dictionary.txt /app/dictionary.txt
CMD ["tail", "-f", "/dev/null"]
```

**Benefits**:
- Docker builds: 2-3 min → < 5 seconds (50x+ faster)
- No build-time execution or resource contention
- Parallel builds work reliably
- Fully reproducible

### Diagnostic Tools

**Submission Package Generator** (`prepare-snorkel-submission-v2.sh`)
- Creates Snorkel-compliant submission zip
- Uses pre-generated data + Dockerfile.snorkel-v2
- Validates all required components

**Public Image Access Test** (`test-public-image-access.sh`)
- Tests if GHCR images are publicly accessible
- Improved error handling (removed `set -e`)
- Fixed container cleanup (no orphaned containers)

**Support Documentation** (`SNORKEL_SUPPORT_TICKET.md`)
- Comprehensive failure analysis
- Architecture comparison
- Diagnostic questions for Snorkel team

## Test Results

### Before
| Environment | Oracle Success | Reward | Status |
|------------|---------------|--------|--------|
| GitHub Actions | 100% (runtime gen) | 1.0 | ✅ |
| Snorkel/Harbor | 60% (data mismatch) | 0.0 | ❌ |

### After
| Environment | Oracle Success | Reward | Status |
|------------|---------------|--------|--------|
| GitHub Actions | 100% (runtime gen) | 1.0 | ✅ |
| Snorkel/Harbor | 100% (pre-gen data) | 1.0 | ✅ |

## Deployment Strategy

### For GitHub Actions CI
- Continue using original `Dockerfile` with GHCR caching
- Oracle generates data at runtime
- Works as before

### For Snorkel Submission
- Use `prepare-snorkel-submission-v2.sh` to create package
- Includes pre-generated data + compliant Dockerfile
- Oracle respects pre-generated files
- All 10 passwords cracked successfully

## Breaking Changes

None - changes are backward compatible:
- GitHub Actions workflow unchanged
- Original Dockerfile still works
- New Snorkel-specific files are additions, not replacements

## Checklist

- [x] Oracle achieves 100% on pre-generated data
- [x] Snorkel-compliant Docker build (< 5 seconds)
- [x] CI artifact download errors fixed
- [x] Container cleanup improved (no orphans)
- [x] Diagnostic tools for Snorkel debugging
- [x] Documentation for both environments
- [x] Backward compatible with existing CI

## Related Issues

Resolves Snorkel evaluation failures:
- NoSuchKey S3 errors (10/13 builds)
- Oracle 0.0 reward (60% success rate)
- Docker build timeouts (2-3 min builds)
