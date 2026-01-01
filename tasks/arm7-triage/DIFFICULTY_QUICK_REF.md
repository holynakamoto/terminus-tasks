# Medium Difficulty Enhancements - Quick Reference

## What Makes This Task Medium Difficulty?

### 1. Dual Target Complexity ⭐⭐⭐
**Before**: Single target (armv7-unknown-linux-gnueabihf)
**After**: Two targets with different linking strategies
- `armv7-unknown-linux-musleabihf` → static linking
- `armv7-unknown-linux-gnueabihf` → dynamic linking

**Why Hard**: Agents must understand musl vs glibc, configure different rustflags, and verify different linking behaviors.

### 2. OpenSSL Cross-Compilation ⭐⭐⭐
**Added**: `openssl = { version = "0.10", features = ["vendored"] }`

**Why Hard**: 
- Requires perl and make (easy to miss)
- Vendored builds are complex
- CC environment variables must be correct
- Common source of cross-compilation failures

### 3. Static Linking Requirements ⭐⭐
**Required rustflags for musl**:
```toml
rustflags = [
  "-C", "target-feature=+crt-static",
  "-C", "link-arg=-static",
  "-C", "link-arg=-no-pie"
]
```

**Why Hard**: Must understand Rust's static linking model and configure rustflags correctly.

### 4. Binary Size Constraint ⭐⭐
**Requirement**: Musl binary must be < 5MB

**Why Hard**: Must balance static linking (increases size) with optimization.

### 5. Configuration Duplication ⭐⭐
**Must match in both files**:
- `/logs/verifier/env.sh`
- `.cargo/config.toml` [env] section

**Why Hard**: Easy to have mismatched values or miss one location.

## Expected Failure Distribution

| Failure Reason | Estimated % |
|----------------|-------------|
| Musl vs glibc confusion | 30-40% |
| OpenSSL cross-compilation | 20-30% |
| Rustflags configuration | 15-25% |
| Binary size constraint | 10-15% |
| Config synchronization | 10-15% |

## Target Pass Rates

- **Oracle**: 100% (must pass)
- **GPT-5**: 45-55%
- **Claude Sonnet 4.5**: 40-50%
- **Combined**: ~50% (Medium difficulty)

## Key Success Factors

Agents must:
1. ✅ Understand musl vs glibc differences
2. ✅ Configure rustflags for static linking
3. ✅ Install perl and make for OpenSSL
4. ✅ Set up pkg-config for cross-compilation
5. ✅ Synchronize env.sh and config.toml
6. ✅ Verify binary properties with readelf

## Quick Test

```bash
# Should pass
harbor run --agent oracle --path arm7-triage

# Should have ~50% pass rate
harbor run -a terminus-2 -m openai/@openai-tbench/gpt-5 -p arm7-triage
```

## Why This Is Fair

- ✅ All requirements explicitly documented
- ✅ Standard tools (rustup, cargo, apt-get)
- ✅ Clear verification commands provided
- ✅ No hidden requirements
- ✅ Incremental testing possible
- ✅ Error messages are informative
