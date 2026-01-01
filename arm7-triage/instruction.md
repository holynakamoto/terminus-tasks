# Rust ARMv7 Cross-Compilation Task

## Overview

You are given a Rust project that is intended to cross-compile to `armv7-unknown-linux-gnueabihf` but currently fails to build. Your objectives are to diagnose and fix the cross-compilation setup for ARMv7 Linux.

This task verifies **three things**:

1. The project can **cross-compile** an ARMv7 Linux (glibc) release binary (build-only; no QEMU execution in tests)
2. The CLI behaves correctly when built and run **natively on the host** (correct output and required error messages)
3. The ARMv7 cross build correctly discovers and links ARM system libraries (not host libraries)

## Objectives

### 1. Install and configure the ARMv7 GCC cross-toolchain

You will need:
- ARM GCC cross-compiler toolchain (`arm-linux-gnueabihf-gcc` and related tools)
- ARM target system libraries for any dependencies your project uses
- Build configuration tools (e.g., `pkg-config`)

**Important:** The project has a dependency on `libz-sys` (zlib compression). You must install the **ARM version** of zlib development files, not just the host x86_64 version. On Debian/Ubuntu systems, this typically means installing packages with the `:armhf` architecture suffix.

### 2. Configure Rust cross-compilation environment

The verifier runs in a separate process and needs to see your environment configuration. You must persist all environment variables by creating `/logs/verifier/env.sh` and exporting them there.

**Required variables** (use absolute paths):
```sh
export CC_armv7_unknown_linux_gnueabihf=/path/to/arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=/path/to/arm-linux-gnueabihf-gcc
```

These tell Rust which compiler and linker to use for the ARM target.

### 3. Configure dependency discovery for cross-compilation

The project depends on `libz-sys`, which needs to find and link the **ARM version** of zlib during the cross-compilation build. This is a common challenge in cross-compilation: build tools must discover target architecture libraries instead of host libraries.

**The problem:** When cross-compiling, dependency discovery tools (like `pkg-config`) default to searching for **host** libraries. You need to configure them to search for **target** libraries instead.

**What you need to figure out:**
- How to tell `pkg-config` that you're cross-compiling (not building natively)
- Where the ARM `.pc` (pkg-config) files and libraries are located on the system
- How to point `pkg-config` to the ARM sysroot and library paths

**Hints:**
- Research how `pkg-config` handles cross-compilation scenarios
- Look for environment variables that control `pkg-config` behavior during cross builds
- The ARM sysroot is typically at a path like `/usr/arm-linux-gnueabihf/` or similar
- You need to tell `pkg-config` to look in ARM-specific paths, not default host paths

**Verification method:**
After building, verify the ARM binary links correctly against ARM libraries:
```bash
readelf -d target/armv7-unknown-linux-gnueabihf/release/sample-cli
```
The `DT_NEEDED` entries must include `libz.so.1`. If you see errors about missing zlib or wrong architecture, your dependency discovery configuration is incorrect.

**All environment variables must be persisted in `/logs/verifier/env.sh`.**

### 4. Configure Cargo for the ARM target

Update `.cargo/config.toml` to ensure the `armv7-unknown-linux-gnueabihf` target uses the correct linker and any necessary linker flags.

### 5. Cross-compile the ARMv7 release binary

Build the ARM binary:
```bash
cargo build --target armv7-unknown-linux-gnueabihf --release
```

The ARMv7 binary must be created at:
- `/app/target/armv7-unknown-linux-gnueabihf/release/sample-cli`

### 6. Build and verify the host (native) binary behavior

Build the native host binary:
```bash
cargo build --release
```

**Required outputs (stdout):**
```bash
$ /app/target/release/sample-cli 5
Result: 10

$ /app/target/release/sample-cli 7
Result: 14
```

**Required error behavior (stderr):**
- Wrong number of arguments → exit non-zero, print usage message containing `Usage:` and `<number>`
- Non-integer argument (e.g., `abc`) → exit non-zero, print exactly: `Error: 'abc' is not a valid integer`

## Project Structure

- The Rust project is located in `/app`
- The CLI binary is named `sample-cli` and takes a single integer argument
- It multiplies the input by 2 and prints the result to stdout

## Common Pitfalls

1. **Linking to host libraries instead of target libraries** - The most common mistake is when the build system finds x86_64 libraries instead of ARM libraries. Use `readelf -d` to verify linkage.

2. **Missing target architecture packages** - Installing `zlib1g-dev` is not enough; you need the ARM version.

3. **Incorrect pkg-config configuration** - If `libz-sys` fails to build with messages about missing zlib, your cross-compilation environment is not properly configured.

4. **Environment variables not persisted** - The verifier runs in a separate process. Variables must be in `/logs/verifier/env.sh` or they won't be seen during verification.

## Success Criteria

Your solution is correct when:
- ✅ ARM binary builds successfully with `cargo build --target armv7-unknown-linux-gnueabihf --release`
- ✅ ARM binary links against `libz.so.1` (verify with `readelf -d`)
- ✅ Host binary builds and produces correct output for valid inputs
- ✅ Host binary produces correct error messages for invalid inputs
- ✅ All environment variables are persisted in `/logs/verifier/env.sh`
