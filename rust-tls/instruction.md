# Rust OpenSSL FFI TLS Client Task (Hard)

## Overview

You are given a Rust project that uses **raw OpenSSL FFI** (via bindgen-generated bindings) to implement an HTTPS client. The project has **multiple subtle bugs** in both the build configuration and the source code that prevent it from working correctly.

This is a **genuinely hard task** that requires:

1. **Proper bindgen configuration** for LLVM 14 and custom OpenSSL paths
2. **Understanding of raw OpenSSL FFI** (not high-level Rust crates)
3. **Fixing subtle bugs** in SSL/TLS connection handling
4. **Ensuring both libssl.so and libcrypto.so are linked** (verifier requirement)
5. **Proper error handling** for all FFI calls
6. **Correct memory management** (no leaks, no double-frees)

## Objectives

### 1. Diagnose and fix build failures

The project fails to build due to multiple issues:

- **bindgen cannot find libclang** - Must use LLVM 14 specifically
- **bindgen cannot find OpenSSL headers** - Custom OpenSSL is in `/opt/openssl`
- **Missing include paths** - LLVM 14 clang headers are in non-standard location
- **Wrong target architecture** - build.rs hardcodes x86_64

### 2. Configure OpenSSL discovery

OpenSSL is installed in a **custom location** (`/opt/openssl`) to simulate a vendored or custom build. You must:

- Create pkg-config files for `/opt/openssl`
- Configure environment variables so `openssl-sys` finds the custom installation
- Ensure runtime linking works (`LD_LIBRARY_PATH` or `ldconfig`)

### 3. Fix bugs in build.rs

The `build.rs` file has several bugs:

- **Missing LLVM 14 clang include path** - bindgen needs `-I/usr/lib/llvm-14/lib/clang/14.0.0/include`
- **Hardcoded target architecture** - should detect `TARGET` environment variable
- **Missing explicit library linking** - should ensure both `libssl` and `libcrypto` are linked
- **No LIBCLANG_PATH verification** - should check LLVM 14 is available

### 4. Fix bugs in https_client.rs

The example has **15+ subtle bugs**:

- **Missing OpenSSL initialization** - `SSL_library_init()` must be called
- **Missing error checks** - Many FFI calls can return NULL or error codes
- **Wrong function signatures** - `wrapper.h` has missing `const` qualifiers
- **Incorrect BIO handling** - BIO ownership and cleanup issues
- **Incomplete SSL_read loop** - Should handle partial reads and SSL_ERROR_WANT_READ
- **Memory leaks** - Missing cleanup in error paths
- **Type mismatches** - Due to incorrect bindgen bindings

### 5. Ensure libssl.so linkage

**CRITICAL:** The verifier requires the binary to be linked against **both** `libssl.so` and `libcrypto.so`. Simply using OpenSSL crypto functions might only link `libcrypto`. You must:

- Use actual SSL/TLS functions (`SSL_connect`, `SSL_read`, `SSL_write`) → forces `libssl` linkage
- Or explicitly link `libssl` in `build.rs` via `cargo:rustc-link-lib=ssl`
- Verify with `ldd` or `readelf -d` that both libraries are present

## Project Structure

```
/app/
├── Cargo.toml          # Dependencies: openssl-sys, bindgen
├── build.rs            # Build script with bindgen configuration (HAS BUGS)
├── wrapper.h            # C header with OpenSSL declarations (HAS BUGS)
├── src/
│   └── lib.rs          # Library code
└── examples/
    └── https_client.rs  # HTTPS client using raw FFI (HAS MANY BUGS)
```

## Expected Behavior

When you run `cargo run --release --example https_client`, it should:

1. **Build successfully** with bindgen generating correct bindings
2. **Connect to `www.rust-lang.org:443`** over TCP
3. **Establish TLS connection** using OpenSSL FFI
4. **Display TLS version** (TLSv1.2 or TLSv1.3)
5. **Print "Successfully connected to https://www.rust-lang.org"**
6. **Display actual HTTP response** with:
   - HTML document structure (`<!DOCTYPE` or `<html>` tags)
   - Rust-lang.org specific content (keywords like "rust-lang", "rustlang", "Rust")
   - Complete HTML tag pairs
   - At least 500 characters of content
7. **Exit with code 0**

## Anti-Cheating Measures

The test suite includes **multiple layers** of verification:

### 1. Binary Analysis
- Verifies binary is linked against OpenSSL from `/opt/openssl` (not system)
- Checks for critical OpenSSL symbols (`SSL_connect`, `SSL_CTX_new`, `SSL_read`/`SSL_write`)
- Ensures bindgen-generated bindings are present

### 2. Network Syscall Verification (STRONGEST)
- Uses `strace` to monitor actual system calls during execution
- Verifies `connect()` syscalls with `AF_INET` (actual network connection)
- Verifies data was sent (`sendto`/`send`/`write`)
- Verifies data was received (`recvfrom`/`recv`/`read`)
- **This prevents agents from simply printing fake HTML output**

### 3. Content Validation
- Checks for real HTML content from rust-lang.org
- Verifies multiple characteristics to make spoofing difficult
- Ensures output length is realistic (>500 characters)

### 4. Build Artifact Verification
- Confirms LLVM 14 is used (not other versions)
- Validates pkg-config files were created
- Checks OpenSSL libraries exist in expected locations

## Key Bugs to Fix

### build.rs Bugs

1. **Missing LLVM 14 clang include path**
   ```rust
   // Should add:
   .clang_arg("-I/usr/lib/llvm-14/lib/clang/14.0.0/include")
   ```

2. **Hardcoded target architecture**
   ```rust
   // Should use:
   let target = env::var("TARGET").unwrap_or_else(|_| "x86_64-unknown-linux-gnu".to_string());
   builder = builder.clang_arg(format!("--target={}", target));
   ```

3. **Missing explicit library linking**
   ```rust
   // Should add:
   println!("cargo:rustc-link-lib=ssl");
   println!("cargo:rustc-link-lib=crypto");
   ```

4. **Missing LIBCLANG_PATH check**
   ```rust
   // Should verify LLVM 14 is available:
   let libclang_path = env::var("LIBCLANG_PATH")
       .unwrap_or_else(|_| "/usr/lib/llvm-14/lib".to_string());
   ```

### wrapper.h Bugs

1. **Missing `const` qualifiers** - Causes type mismatches in bindgen output
2. **Missing function declarations** - Some OpenSSL functions not declared

### https_client.rs Bugs

1. **Missing `SSL_library_init()`** - Must initialize OpenSSL before use
2. **Missing error checks** - Many FFI calls can fail (NULL returns, error codes)
3. **Incorrect BIO handling** - BIO ownership issues, potential double-free
4. **Incomplete read loop** - Should handle partial reads and SSL errors
5. **Memory leaks** - Missing cleanup in error paths
6. **Type mismatches** - Due to incorrect bindgen bindings from wrapper.h bugs

## Common Pitfalls

1. **Using high-level `openssl` crate** - This task requires raw FFI via bindgen
2. **Wrong LLVM version** - Must use LLVM 14, not system default
3. **Missing libssl.so linkage** - Verifier requires both `libssl` and `libcrypto`
4. **Fake output** - `strace` verification catches fake connections
5. **Incorrect error handling** - OpenSSL FFI requires careful error checking
6. **Memory leaks** - Must properly free all SSL/BIO/CTX objects

## Success Criteria

Your solution is correct when:

- ✅ Project builds successfully with `cargo build --release`
- ✅ Bindgen generates bindings using LLVM 14
- ✅ Binary links against OpenSSL from `/opt/openssl` (verify with `ldd`)
- ✅ Binary contains OpenSSL symbols (`SSL_connect`, `SSL_CTX_new`, etc.)
- ✅ Example runs and connects to `www.rust-lang.org:443`
- ✅ TLS version is displayed correctly
- ✅ Real HTTP response is received and displayed
- ✅ `strace` shows actual network syscalls
- ✅ No memory leaks or crashes

## Difficulty Notes

This task is **genuinely hard** because it requires:

- Deep understanding of **raw FFI** and C interop
- Knowledge of **OpenSSL API** (not just Rust wrappers)
- Ability to **debug bindgen configuration** issues
- Understanding of **memory management** in unsafe Rust
- Multiple interdependent fixes (15+ bugs across 3 files)
- **Real network connectivity** (can't fake with static strings)
- **Multiple anti-cheat layers** (strace, symbols, content validation)

Expected solve rate: **<30%** for frontier models.
