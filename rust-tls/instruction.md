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
- Exit with code 0

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

