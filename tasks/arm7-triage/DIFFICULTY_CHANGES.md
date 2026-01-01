# Difficulty Enhancement Changes

## Target Difficulty: Medium (<60% pass rate)

### Changes Made to Increase Difficulty

#### 1. **Dual Target Requirement** (Major)
- **Before**: Single target (`armv7-unknown-linux-gnueabihf`)
- **After**: Two targets with different linking strategies:
  - `armv7-unknown-linux-musleabihf` (static linking)
  - `armv7-unknown-linux-gnueabihf` (dynamic linking)
- **Why this increases difficulty**: Agents must understand the difference between musl and glibc, configure rustflags differently for each target, and handle static vs dynamic linking correctly.

#### 2. **OpenSSL Dependency** (Major)
- **Before**: Only `libz-sys` (simple C library)
- **After**: Added `openssl` with vendored feature
- **Why this increases difficulty**: OpenSSL is notoriously difficult to cross-compile. Even with vendored sources, it requires:
  - Additional build tools (perl, make)
  - Correct CC environment variables
  - Proper cross-compilation configuration
  - Understanding of how vendored builds work in Rust

#### 3. **Static Linking Requirements** (Medium)
- **Before**: No specific linking requirements
- **After**: Musl target must be fully statically linked with specific rustflags:
  - `-C target-feature=+crt-static`
  - `-C link-arg=-static`
  - `-C link-arg=-no-pie`
- **Why this increases difficulty**: Agents must:
  - Understand Rust's static linking model
  - Know how to configure rustflags in `.cargo/config.toml`
  - Verify static linking with `readelf -l` (no INTERP segment)

#### 4. **Binary Size Constraint** (Medium)
- **Before**: No size requirements
- **After**: Musl binary must be under 5MB
- **Why this increases difficulty**: Agents must:
  - Understand that release builds should be optimized
  - Potentially use strip or other size reduction techniques
  - Balance static linking (increases size) with optimization

#### 5. **Explicit CPU Feature Requirements** (Low-Medium)
- **Before**: Generic ARMv7 compilation
- **After**: Documentation mentions ARMv7-A with VFPv3-D16 hard-float
- **Why this increases difficulty**: Agents must understand ARM CPU features and ensure correct target selection

#### 6. **Configuration Duplication Requirement** (Medium)
- **Before**: Environment variables in one place
- **After**: Must duplicate all 5 environment variables in both:
  - `/logs/verifier/env.sh`
  - `.cargo/config.toml` [env] section
- **Why this increases difficulty**: Easy to miss one location or have mismatched values. Tests explicitly verify both files match.

### Expected Failure Modes

Agents are likely to fail due to:

1. **Musl vs Glibc Confusion** (30-40% failure rate)
   - Building only one target
   - Using wrong rustflags for each target
   - Not understanding static vs dynamic linking

2. **OpenSSL Cross-Compilation** (20-30% failure rate)
   - Missing build dependencies (perl, make)
   - Incorrect CC environment variables
   - Vendored build failures

3. **Rustflags Configuration** (15-25% failure rate)
   - Missing or incorrect rustflags in `.cargo/config.toml`
   - Not understanding `-C target-feature=+crt-static`
   - Forgetting `-C link-arg=-no-pie`

4. **Binary Size Constraint** (10-15% failure rate)
   - Not optimizing for size
   - Including debug symbols
   - Not using release mode correctly

5. **Configuration Synchronization** (10-15% failure rate)
   - Environment variables in env.sh don't match .cargo/config.toml
   - Missing variables in one location
   - Using relative paths instead of absolute paths

### Estimated Pass Rates

- **GPT-5**: 45-55% (should handle most complexity but may struggle with musl/glibc distinction)
- **Claude Sonnet 4.5**: 40-50% (strong at cross-compilation but OpenSSL may cause issues)
- **Combined**: ~50% (target: <60% for medium difficulty)

### Why This Remains Fair

Despite increased difficulty, the task remains fair because:

1. **Clear Documentation**: All requirements are explicitly stated in `instruction.md`
2. **Verifiable Steps**: Each requirement can be verified with standard tools (`readelf`, `file`, `ls`)
3. **No Hidden Requirements**: All constraints are documented upfront
4. **Standard Tools**: Uses well-known tools (rustup, cargo, apt-get)
5. **Incremental Testing**: Agents can test each target independently
6. **Error Messages**: Build failures provide clear feedback about what's wrong

### Validation

To validate this difficulty level:

```bash
# Run oracle (should pass)
harbor run --agent oracle --path arm7-triage

# Run against frontier models (should have ~50% pass rate)
harbor run -a terminus-2 -m openai/@openai-tbench/gpt-5 -p arm7-triage
harbor run -a terminus-2 -m openai/@anthropic-tbench/claude-sonnet-4-5-20250929 -p arm7-triage
```

Expected results:
- Oracle: 100% pass rate
- GPT-5: 45-55% pass rate (5 runs)
- Claude Sonnet 4.5: 40-50% pass rate (5 runs)
