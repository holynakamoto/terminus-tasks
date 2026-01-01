# Task Difficulty Enhancement Summary

## Objective
Increase task difficulty from Easy (>80%) to Medium (<60% pass rate) for frontier AI models.

## Files Modified

### 1. `Cargo.toml`
- **Added**: `openssl = { version = "0.10", features = ["vendored"] }`
- **Reason**: OpenSSL is notoriously difficult to cross-compile, even with vendored sources

### 2. `src/main.rs`
- **Added**: `let _ = openssl::version::version();` to force OpenSSL linking
- **Reason**: Ensures OpenSSL is actually compiled and linked, not just declared as dependency

### 3. `instruction.md`
- **Changed**: Overview to mention both musl and glibc targets
- **Added**: Requirement for ARMv7-A with VFPv3-D16 CPU features
- **Added**: Static linking requirements for musl target
- **Added**: Binary size constraint (under 5MB for musl)
- **Added**: Specific rustflags requirements
- **Updated**: Build instructions for both targets
- **Updated**: Verification steps for static vs dynamic linking
- **Updated**: Success criteria to include both targets

### 4. `tests/test_outputs.py`
- **Modified**: `test_armv7_cross_build_artifacts_exist_build_only()` to:
  - Build both musl and glibc targets
  - Verify musl binary is statically linked (no INTERP segment)
  - Verify musl binary size is under 5MB
  - Verify glibc binary dynamically links libz.so.1
  - Check both binaries are ARM ELF executables

### 5. `solution/solve.sh`
- **Added**: `perl` and `make` to apt-get install (required for OpenSSL vendored builds)
- **Note**: Already had support for both targets, just needed build tools

### 6. `tests/test.sh`
- **Simplified**: Reward logic (minor cleanup, no functional change)

## New Requirements Summary

### Must Build Two Targets:
1. **armv7-unknown-linux-musleabihf** (musl/static)
   - Fully statically linked
   - No INTERP segment
   - Under 5MB in size
   - Requires rustflags: `-C target-feature=+crt-static`, `-C link-arg=-static`, `-C link-arg=-no-pie`

2. **armv7-unknown-linux-gnueabihf** (glibc/dynamic)
   - Dynamically linked
   - Must link against libz.so.1
   - Standard dynamic linking

### Must Handle OpenSSL:
- Vendored OpenSSL build during cross-compilation
- Requires perl and make
- Requires correct CC environment variables

### Must Configure Both Files:
- `/logs/verifier/env.sh` - Shell environment variables
- `.cargo/config.toml` - Cargo build configuration with [env] section
- All 5 environment variables must match in both files

## Difficulty Factors

### High Complexity (30-40% failure rate):
- Understanding musl vs glibc
- Configuring static vs dynamic linking
- Setting correct rustflags for each target

### Medium Complexity (20-30% failure rate):
- OpenSSL cross-compilation with vendored sources
- Installing correct build dependencies
- Environment variable configuration

### Low-Medium Complexity (10-20% failure rate):
- Binary size optimization
- Configuration synchronization between files
- Absolute path requirements

## Expected Pass Rate: 40-55%

This should place the task solidly in the Medium difficulty range (<60%).

## Testing

To validate:
```bash
# Oracle should pass
harbor run --agent oracle --path arm7-triage

# Frontier models should have ~50% pass rate
harbor run -a terminus-2 -m openai/@openai-tbench/gpt-5 -p arm7-triage
harbor run -a terminus-2 -m openai/@anthropic-tbench/claude-sonnet-4-5-20250929 -p arm7-triage
```
