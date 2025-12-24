# Rust OpenSSL Build Configuration Task

## Overview

You are given a Rust project that fails to build due to system dependency configuration issues. The build errors are not straightforward and require careful diagnosis to identify the root causes.

## Objectives

1. **Diagnose the build failures:**
   - Investigate why `openssl-sys` cannot find OpenSSL
   - Determine why `bindgen` cannot find libclang
   - Understand what's actually missing vs. what's misconfigured

2. **Resolve the dependency issues:**
   - Install the correct system packages (note: some may already be installed but wrong versions)
   - **IMPORTANT:** You must use LLVM 14 specifically for libclang. The system has LLVM 14 available at `/usr/lib/llvm-14/`. Bindgen requires libclang from LLVM 14, not other versions.
   - Configure environment variables appropriately
   - Ensure pkg-config can locate required libraries

3. **Build the project successfully:**
   ```bash
   cargo build --release
   ```

4. **Verify the HTTPS client example works:**
   ```bash
   cargo run --release --example https_client
   ```
   The example should successfully connect to `https://www.rust-lang.org` and display:
   - "Successfully connected to https://www.rust-lang.org"
   - "TLS version: TLSv1.2" or higher

## Project Structure

The Rust project is located in `/app` with the following structure:
```
/app/
├── Cargo.toml
├── build.rs
├── wrapper.h
├── src/
│   └── lib.rs
└── examples/
    └── https_client.rs
```

## Expected Behavior

When you run `cargo run --release --example https_client`, it should:
- Successfully build the project
- Connect to `https://www.rust-lang.org` over HTTPS
- Display the TLS version (TLSv1.2 or higher)
- Print "Successfully connected to https://www.rust-lang.org"
- Display actual HTTP response content from rust-lang.org with ALL of the following:
  - HTML document structure (must include both `<!DOCTYPE` or `<html>` tags)
  - Rust-lang.org specific content (keywords like "rust-lang", "rustlang", or "Rust")
  - Complete HTML tag pairs (both opening tags like `<tag>` and closing tags like `</tag>`)
  - At least 500 characters of content (indicating a real webpage was fetched, not just a static string)
- Exit with code 0

**Note:** The output validation ensures that a real TLS connection is established, not just simulated output. The presence of actual HTML content from rust-lang.org proves the connection is genuine.

## Anti-Cheating Measures

The test suite includes multiple layers of verification to ensure a real TLS connection is made:

1. **Binary Analysis:**
   - Verifies the binary is linked against OpenSSL libraries from `/opt/openssl`
   - Checks for critical OpenSSL symbols (`SSL_connect`, `SSL_CTX_new`, `SSL_read`/`SSL_write`) in the binary
   - Ensures bindgen-generated bindings are present

2. **Network Syscall Verification (Strongest):**
   - Uses `strace` to monitor actual system calls during execution
   - Verifies `connect()` syscalls with `AF_INET` (actual network connection)
   - Verifies data was sent over the network (`sendto`/`send`/`write`)
   - Verifies data was received from the network (`recvfrom`/`recv`/`read`)
   - **This prevents agents from simply printing fake HTML output**

3. **Content Validation:**
   - Checks for real HTML content from rust-lang.org
   - Verifies multiple characteristics to make spoofing difficult
   - Ensures output length is realistic (>200 characters)

4. **Build Artifact Verification:**
   - Confirms LLVM 14 is used (not other versions)
   - Validates pkg-config files were created
   - Checks OpenSSL libraries exist in expected locations

## Expected Build Artifacts

After successfully resolving the build configuration, the following should be present:

1. **Bindgen-generated bindings:**
   - The build process should generate `bindings.rs` files in the `./target/release/build` directory
   - This confirms that bindgen successfully found libclang and generated FFI bindings

2. **OpenSSL pkg-config file:**
   - `/opt/openssl/lib/pkgconfig/openssl.pc` - this file enables pkg-config to locate the OpenSSL installation
   - This is necessary for the `openssl-sys` crate to find the OpenSSL headers and libraries

3. **OpenSSL libraries:**
   - `/opt/openssl/lib/libssl.so` (or versioned variants like `libssl.so.3`, `libssl.so.1.1`)
   - `/opt/openssl/lib/libcrypto.so` (or versioned variants)

4. **Compiled binary:**
   - The binary should be linked against the OpenSSL libraries from `/opt/openssl`
   - Verify with: `ldd ./target/release/examples/https_client` (should show libssl and libcrypto)

## Important Notes

- Some dependencies may already be installed, but in incorrect versions or locations
- The error messages may not immediately reveal the root cause
- You may need to investigate library locations and version compatibility
- Environment variables need to be set correctly for both compile-time and runtime
- pkg-config configuration may require manual intervention

