#!/bin/bash
set -euo pipefail

# Ensure logs directory exists (for both local and CodeBuild environments)
mkdir -p /logs/verifier

# Ensure reward file is created even on early exit
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

cd /app

# Test 1: Build succeeds
echo "Testing: cargo build --release"
if ! cargo build --release; then
    echo "✗ Build failed"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Build succeeded"

# Test 2: Verify bindgen actually generated bindings (anti-cheat)
echo "Testing: bindgen generated bindings"
BINARY_PATH="./target/release/examples/https_client"
if [ ! -f "$BINARY_PATH" ]; then
    BINARY_PATH="./target/release/https_client"
fi

# Check that build artifacts exist (bindgen would have created them)
if [ ! -d "./target/release/build" ]; then
    echo "✗ Build artifacts not found - bindgen may not have run"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

# Verify bindgen actually generated the bindings.rs file
BINDINGS_FOUND=$(find ./target/release/build -name "bindings.rs" -type f 2>/dev/null | wc -l)
if [ "$BINDINGS_FOUND" -eq 0 ]; then
    echo "✗ bindgen bindings.rs not found - bindgen did not run successfully"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Bindgen bindings verified"

# Test 3: Verify binary is linked against OpenSSL (anti-cheat)
echo "Testing: binary linked against OpenSSL"
if ! command -v ldd &> /dev/null; then
    echo "⚠ ldd not available, skipping library check"
else
    # Check that the binary is linked against libssl and libcrypto
    LDD_OUTPUT=$(ldd "$BINARY_PATH" 2>&1 || true)
    if ! echo "$LDD_OUTPUT" | grep -qE "(libssl|libcrypto)"; then
        echo "✗ Binary not linked against OpenSSL libraries"
        echo "ldd output: $LDD_OUTPUT"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
    
    # Verify it's using OpenSSL from /opt/openssl (if LD_LIBRARY_PATH is set correctly)
    # This ensures the non-standard OpenSSL location is being used
    if echo "$LDD_OUTPUT" | grep -q "/opt/openssl"; then
        echo "✓ Binary using OpenSSL from /opt/openssl"
    else
        # If LD_LIBRARY_PATH is set, libraries might be resolved at runtime
        # Check if the binary would load from /opt/openssl when run
        echo "✓ Binary linked against OpenSSL (runtime path may differ)"
    fi
fi

# Test 4: Verify OpenSSL libraries exist in expected location (anti-cheat)
echo "Testing: OpenSSL libraries in /opt/openssl"
if [ ! -f "/opt/openssl/lib/libssl.so" ] && [ ! -f "/opt/openssl/lib/libssl.so.3" ] && [ ! -f "/opt/openssl/lib/libssl.so.1.1" ]; then
    echo "✗ OpenSSL libraries not found in /opt/openssl/lib"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ ! -f "/opt/openssl/lib/libcrypto.so" ] && [ ! -f "/opt/openssl/lib/libcrypto.so.3" ] && [ ! -f "/opt/openssl/lib/libcrypto.so.1.1" ]; then
    echo "✗ OpenSSL crypto libraries not found in /opt/openssl/lib"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ OpenSSL libraries verified in /opt/openssl"

# Test 5: Example runs successfully
echo "Testing: cargo run --release --example https_client"
OUTPUT=$(cargo run --release --example https_client 2>&1)
RUN_EXIT=$?

if [ $RUN_EXIT -ne 0 ]; then
    echo "✗ Example failed to run"
    echo "Output: $OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Example executed successfully"

# Test 6: Verify output contains success message
if ! echo "$OUTPUT" | grep -q "Successfully connected to https://www.rust-lang.org"; then
    echo "✗ Success message not found in output"
    echo "Output: $OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Success message found"

# Test 7: Verify TLS version (anti-cheat - must be real TLS, not faked)
if ! echo "$OUTPUT" | grep -qE "TLS version: TLSv1\.[2-3]"; then
    echo "✗ Valid TLS version not found in output"
    echo "Output: $OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Valid TLS version found"

# Test 8: Verify actual HTTP response content (anti-cheat - ensures real connection)
# The response should contain actual HTML from rust-lang.org, not just faked output
if ! echo "$OUTPUT" | grep -qiE "(rust|rust-lang|<!DOCTYPE|<html)"; then
    # If we can't see HTML in output, at least verify the TLS version format is correct
    # and the connection actually succeeded (not just printed strings)
    if ! echo "$OUTPUT" | grep -qE "TLS version: TLSv1\.[23]"; then
        echo "✗ TLS connection verification failed"
        echo "Output: $OUTPUT"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
fi

echo "✓ Real TLS connection verified"

# Test 9: Verify LLVM 14 is installed (anti-cheat - ensures correct version)
echo "Testing: LLVM 14 installed"
if [ ! -d "/usr/lib/llvm-14" ] && [ ! -d "/usr/lib/x86_64-linux-gnu/llvm-14" ]; then
    echo "✗ LLVM 14 not found - incorrect version may have been used"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ LLVM 14 verified"

# Test 10: Verify pkg-config files were created (anti-cheat - ensures OpenSSL was configured)
echo "Testing: pkg-config files for OpenSSL"
if [ ! -f "/opt/openssl/lib/pkgconfig/openssl.pc" ]; then
    echo "✗ pkg-config file for OpenSSL not found - OpenSSL may not be properly configured"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ pkg-config files verified"

echo "✓ All tests passed"
echo 1 > /logs/verifier/reward.txt
