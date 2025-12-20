# Rust ARMv7 Cross-Compilation Task

## Overview

You are given a Rust project that is intended to cross-compile to `armv7-unknown-linux-gnueabihf` but currently fails to build and/or run. Your objectives are to diagnose and fix the cross-compilation setup for ARMv7 Linux.

## Objectives

1. **Install and configure the ARMv7 GCC cross-toolchain** (if not already configured)
   - Ensure `arm-linux-gnueabihf-gcc` and related tools are available

2. **Set correct environment variables for Rust's target toolchain:**
   - `CC_armv7_unknown_linux_gnueabihf` should point to the ARM GCC compiler
   - `CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER` should point to the ARM linker

3. **Update `.cargo/config.toml`** to ensure the `armv7-unknown-linux-gnueabihf` target uses the correct linker and flags

4. **Build the project** successfully:
   ```bash
   cargo build --target armv7-unknown-linux-gnueabihf --release
   ```

5. **Verify the binary works** using QEMU user-mode:
   - Execute the produced ARM binary: `./target/armv7-unknown-linux-gnueabihf/release/sample-cli <number>`
   - The binary should print `Result: <number * 2>` and exit successfully
   - Example: `./target/armv7-unknown-linux-gnueabihf/release/sample-cli 5` should print `Result: 10`

## Project Structure

- The Rust project is located in `/app`
- The CLI binary is named `sample-cli` and takes a single integer argument
- It multiplies the input by 2 and prints the result

## Expected Behavior

When you run the binary via QEMU, it should:
- Accept a single integer command-line argument
- Print `Result: <number * 2>` to stdout
- Exit with code 0

## QEMU Execution

Use QEMU user-mode to run the ARM binary. The command will typically be:
```bash
qemu-arm -L /usr/arm-linux-gnueabihf ./target/armv7-unknown-linux-gnueabihf/release/sample-cli <input>
```

Note: The exact QEMU command may vary based on your system configuration, but you need to ensure the ARM binary runs correctly and produces the expected output.

