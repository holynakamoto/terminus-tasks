# Rust ARMv7 Cross-Compilation Task

## Overview

You are given a Rust project that is intended to cross-compile to `armv7-unknown-linux-gnueabihf` but currently fails to build and/or run. Your objectives are to diagnose and fix the cross-compilation setup for ARMv7 Linux.

This task verifies **two things**:

1. The project can **cross-compile** an ARMv7 Linux (glibc) release binary (build-only; no QEMU execution in tests).
2. The CLI behaves correctly when built and run **natively on the host** (correct output and required error messages).

## Objectives

1. **Install and configure the ARMv7 GCC cross-toolchain** (if not already configured)
   - Ensure `arm-linux-gnueabihf-gcc` and related tools are available

2. **Set correct environment variables for Rust's target toolchain (persisted for the verifier):**

   The verifier runs in a separate process and will only reliably see these variables if you persist them by creating `/logs/verifier/env.sh` and exporting them there.

   Create `/logs/verifier/env.sh` with:

   ```sh
   export CC_armv7_unknown_linux_gnueabihf=/path/to/arm-linux-gnueabihf-gcc
   export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=/path/to/arm-linux-gnueabihf-gcc
   ```

   Requirements:
   - `CC_armv7_unknown_linux_gnueabihf` must point to the ARM GCC compiler (typically `arm-linux-gnueabihf-gcc`)
   - `CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER` must point to the ARM linker driver (typically also `arm-linux-gnueabihf-gcc`)

3. **Update `.cargo/config.toml`** to ensure the `armv7-unknown-linux-gnueabihf` target uses the correct linker and flags

4. **Cross-compile ARMv7 release binary (build-only check):**
   ```bash
   cargo build --target armv7-unknown-linux-gnueabihf --release
   ```
   The ARMv7 binary must exist at:
   - `/app/target/armv7-unknown-linux-gnueabihf/release/sample-cli`

5. **Build + run the host (native) release binary and verify CLI behavior:**
   ```bash
   cargo build --release
   /app/target/release/sample-cli 5
   /app/target/release/sample-cli 7
   ```
   Required outputs (stdout):
   - Input `5` prints exactly: `Result: 10`
   - Input `7` prints exactly: `Result: 14`

6. **Verify required error behavior on the host binary:**
   - If called with the wrong number of arguments, it must exit non-zero and print the following to **stderr**:
     - A usage line containing `Usage:`
     - The placeholder `<number>` in the usage message
   - If called with a non-integer argument (e.g. `abc`), it must exit non-zero and print exactly this to **stderr**:
     - `Error: 'abc' is not a valid integer`

## Project Structure

- The Rust project is located in `/app`
- The CLI binary is named `sample-cli` and takes a single integer argument
- It multiplies the input by 2 and prints the result

## Expected Behavior (host binary)

When you run the host binary (built without `--target`), it should:
- Accept a single integer command-line argument
- Print `Result: <number * 2>` to stdout
- Exit with code 0

If invoked incorrectly, it should:
- Print a usage message to stderr and exit non-zero when arguments are missing/wrong
- Print `Error: '<arg>' is not a valid integer` to stderr and exit non-zero when parsing fails

