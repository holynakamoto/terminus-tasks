# Rust ARMv7 Cross-Compilation Task

## Overview

You are given a Rust project that is intended to cross-compile to ARMv7 Linux targets but currently fails to build. Your task is to diagnose and fix the cross-compilation setup for **both** ARMv7 musl (static) and ARMv7 glibc (dynamic) targets.

The task verifies that:
1. The project can **cross-compile** ARMv7 Linux binaries for both musl (static) and glibc (dynamic) targets
2. The musl binary is fully statically linked and under 5MB in size
3. The glibc binary correctly links ARM system libraries (not host libraries)
4. The CLI behaves correctly when built and run **natively on the host**

## Objectives

### 1. Install the ARMv7 cross-compilation toolchain

You will need to install:
- ARM GCC cross-compiler toolchain and related build tools (for glibc target: `gcc-arm-linux-gnueabihf`, `binutils-arm-linux-gnueabihf`, etc.)
- **ARM musl cross-compiler toolchain** (for musl target) - see instructions below
- ARM target libraries for project dependencies (the project uses zlib compression and OpenSSL)
- Build configuration tools

**Installing the musl cross-compiler:**

The musl cross-compiler (`arm-linux-musleabihf-gcc`) is not available in standard Debian/Ubuntu repositories. You need to build it using `musl-cross-make`:

1. Install dependencies:
   ```bash
   apt-get install -y git make gcc g++ bash patch xz-utils
   ```

2. Build and install the musl cross-compiler:
   ```bash
   git clone https://github.com/richfelker/musl-cross-make.git
   cd musl-cross-make
   ```
   
   Create a `config.mak` file:
   ```makefile
   TARGET = arm-linux-musleabihf
   OUTPUT = /usr
   COMMON_CONFIG += CFLAGS="-g0 -Os" CXXFLAGS="-g0 -Os" LDFLAGS="-s"
   GCC_CONFIG += --with-arch=armv7-a --with-fpu=vfpv3-d16
   ```
   
   Build and install:
   ```bash
   make install
   ```
   
   This will install `arm-linux-musleabihf-gcc` to `/usr/bin/arm-linux-musleabihf-gcc`.

**Note:** When installing development libraries for cross-compilation on Debian/Ubuntu systems, you typically need packages built for the target architecture, not just the host architecture. The project uses OpenSSL with vendored sources, which requires additional build tools.

### 2. Configure Rust cross-compilation

The verifier runs in a separate process and needs to see your configuration. You must create:
- **`/logs/verifier/env.sh`** - Shell script with environment variables (will be sourced by the verifier)
- **`.cargo/config.toml`** - Cargo build configuration

Your configuration needs to handle:
- Specifying the compiler and linker for **both** ARM targets (musl and glibc)
- Enabling cross-compilation for build scripts that use `pkg-config`
- Ensuring build scripts find ARM libraries instead of host libraries
- Configuring static linking for the musl target

**Important:** The verifier and Cargo build process are separate. Configuration that works for one may not automatically work for the other. Any environment variables you set for Cargo must match those used by the verifier.

**Critical:** The musl target requires specific rustflags for static linking:
- `-C target-feature=+crt-static` - Enable static C runtime
- `-C link-arg=-static` - Force static linking
- `-C link-arg=-no-pie` - Disable position-independent executable

### 3. Build both ARM release binaries

Cross-compile the project for **both** targets:

**Musl (static) target:**
```bash
cargo build --target armv7-unknown-linux-musleabihf --release
```

The ARMv7 musl binary must be created at:
- `/app/target/armv7-unknown-linux-musleabihf/release/sample-cli`

**Glibc (dynamic) target:**
```bash
cargo build --target armv7-unknown-linux-gnueabihf --release
```

The ARMv7 glibc binary must be created at:
- `/app/target/armv7-unknown-linux-gnueabihf/release/sample-cli`

**Verify the musl build is statically linked:**
```bash
readelf -d target/armv7-unknown-linux-musleabihf/release/sample-cli
```
Should show NO dynamic section (fully static).

**Verify the musl binary size:**
```bash
ls -lh target/armv7-unknown-linux-musleabihf/release/sample-cli
```
Must be under 5MB.

**Verify the glibc build is correct:**
```bash
readelf -d target/armv7-unknown-linux-gnueabihf/release/sample-cli
```

The glibc binary must link against `libz.so.1` (zlib). If you see linking errors or wrong architecture warnings, your cross-compilation environment is misconfigured.

### 4. Build and test the host binary

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

## Debugging Tips

If the build fails:
- Check that you've installed all necessary packages for the target architecture
- Verify environment variables are set correctly in both configuration files
- Use `readelf -d` to inspect what libraries the binary actually links against
- Use `readelf -l` to check for INTERP segment (should be absent in musl binary)
- Review build script output carefully - it often indicates which libraries it's trying to find
- For musl builds, ensure all rustflags for static linking are set correctly
- For OpenSSL vendored builds, ensure you have perl and make installed
- Check binary size with `ls -lh` - musl binary must be under 5MB

## Success Criteria

Your solution is correct when:
- ✅ ARM musl binary builds successfully with `cargo build --target armv7-unknown-linux-musleabihf --release`
- ✅ ARM musl binary is fully statically linked (no INTERP segment, no dynamic section)
- ✅ ARM musl binary is under 5MB in size
- ✅ ARM glibc binary builds successfully with `cargo build --target armv7-unknown-linux-gnueabihf --release`
- ✅ ARM glibc binary links against `libz.so.1` (verify with `readelf -d`)
- ✅ Both ARM binaries are 32-bit ARM ELF executables
- ✅ Host binary builds and produces correct output for valid inputs
- ✅ Host binary produces correct error messages for invalid inputs
- ✅ Required environment configuration is in `/logs/verifier/env.sh`
- ✅ Cargo configuration is in `.cargo/config.toml` with correct rustflags for both targets
