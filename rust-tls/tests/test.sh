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
# Test 2: Verify bindgen generated bindings (anti-cheat)
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
# Test 3: Verify binary is linked against OpenSSL from /opt/openssl (REQUIRED)
echo "Testing: binary uses OpenSSL from /opt/openssl (not system)"
if ! command -v ldd &> /dev/null; then
    echo "✗ ldd not available - cannot verify OpenSSL linking"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
# Check that the binary is linked against libssl and libcrypto
LDD_OUTPUT=$(ldd "$BINARY_PATH" 2>&1 || true)
if ! echo "$LDD_OUTPUT" | grep -qE "(libssl|libcrypto)"; then
    echo "✗ Binary not linked against OpenSSL libraries"
    echo "ldd output: $LDD_OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
# REQUIRED: Must link to /opt/openssl, NOT system OpenSSL
if ! echo "$LDD_OUTPUT" | grep -q "/opt/openssl"; then
    if echo "$LDD_OUTPUT" | grep -qE "/usr/lib.*libssl"; then
        echo "✗ Binary using system OpenSSL instead of /opt/openssl"
        echo "ldd output: $LDD_OUTPUT"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
    echo "✗ Binary not using OpenSSL from /opt/openssl"
    echo "ldd output: $LDD_OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ Binary correctly using OpenSSL from /opt/openssl"
# Additional check: Verify OpenSSL symbols are present in the binary
echo "Testing: OpenSSL symbols in binary"
if command -v nm &> /dev/null; then
    NM_OUTPUT=$(nm -D "$BINARY_PATH" 2>&1 || true)
    SYMBOL_COUNT=0
    if echo "$NM_OUTPUT" | grep -q "SSL_connect"; then
        SYMBOL_COUNT=$((SYMBOL_COUNT + 1))
    fi
    if echo "$NM_OUTPUT" | grep -q "SSL_CTX_new"; then
        SYMBOL_COUNT=$((SYMBOL_COUNT + 1))
    fi
    if echo "$NM_OUTPUT" | grep -qE "SSL_read|SSL_write"; then
        SYMBOL_COUNT=$((SYMBOL_COUNT + 1))
    fi
    if [ $SYMBOL_COUNT -lt 2 ]; then
        echo "✗ Insufficient OpenSSL symbols found in binary (found $SYMBOL_COUNT/3 expected)"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
    echo "✓ OpenSSL symbols verified ($SYMBOL_COUNT/3 critical symbols found)"
else
    echo "⚠ nm not available, skipping symbol check"
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
# Test 5: Example runs successfully (using the built binary directly)
echo "Testing: $BINARY_PATH"
OUTPUT=$("$BINARY_PATH" 2>&1)
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
HTML_CHECKS_PASSED=0
if echo "$OUTPUT" | grep -qiE "<!DOCTYPE|<html"; then
    HTML_CHECKS_PASSED=$((HTML_CHECKS_PASSED + 1))
else
    echo "✗ No HTML tags found in output"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if echo "$OUTPUT" | grep -qiE "(rust-lang|rustlang|Rust)"; then
    HTML_CHECKS_PASSED=$((HTML_CHECKS_PASSED + 1))
else
    echo "✗ No rust-lang.org content found in output"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if echo "$OUTPUT" | grep -qiE "<[a-z]+[^>]*>" && echo "$OUTPUT" | grep -qiE "</[a-z]+>"; then
    HTML_CHECKS_PASSED=$((HTML_CHECKS_PASSED + 1))
else
    echo "✗ No complete HTML tag pairs found"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ ${#OUTPUT} -ge 500 ]; then
    HTML_CHECKS_PASSED=$((HTML_CHECKS_PASSED + 1))
else
    echo "✗ Output too short (${#OUTPUT} chars, expected >=500)"
    echo "Output preview: ${OUTPUT:0:200}"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ $HTML_CHECKS_PASSED -ne 4 ]; then
    echo "✗ Not all HTML checks passed ($HTML_CHECKS_PASSED/4)"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ Real TLS connection verified (4/4 checks passed)"
# Test 10: Verify LLVM 14 is installed AND actually used (anti-cheat - ensures correct version)
echo "Testing: LLVM 14 installed and used by bindgen"
if [ ! -d "/usr/lib/llvm-14" ] && [ ! -d "/usr/lib/x86_64-linux-gnu/llvm-14" ]; then
    echo "✗ LLVM 14 not found - incorrect version may have been used"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ ! -f "/usr/lib/llvm-14/lib/libclang.so" ] && [ ! -f "/usr/lib/x86_64-linux-gnu/libclang-14.so.1" ]; then
    echo "✗ LLVM 14 libclang not found - bindgen may have used wrong version"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ -d "./target/release/build" ]; then
    # Optional: check build logs for clang version if available.
    # Under `set -e`, `xargs` may exit non-zero when there is no input/match; treat that as "no version info found".
    CLANG_VERSION_CHECK=$(find ./target/release/build -name "output" -o -name "stderr" 2>/dev/null | xargs grep -l "clang version" 2>/dev/null | head -1 || true)
    if [ -n "$CLANG_VERSION_CHECK" ]; then
        if ! grep -q "clang version 14" "$CLANG_VERSION_CHECK"; then
            echo "✗ Build used wrong clang version (not 14)"
            cat "$CLANG_VERSION_CHECK"
            echo 0 > /logs/verifier/reward.txt
            exit 1
        fi
        echo "✓ Clang version 14 confirmed in build logs"
    else
        echo "⚠ No clang version in build logs (common — skipping detailed check)"
    fi
else
    echo "⚠ No build directory — skipping clang version log check"
fi
echo "✓ LLVM 14 verified and available for bindgen"
# Test 11: Verify pkg-config files were created (anti-cheat - ensures OpenSSL was configured)
echo "Testing: pkg-config files for OpenSSL"
if [ ! -f "/opt/openssl/lib/pkgconfig/openssl.pc" ]; then
    echo "✗ pkg-config file for OpenSSL not found - OpenSSL may not be properly configured"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ pkg-config files verified"
echo "✓ All tests passed"
echo 1 > /logs/verifier/reward.txt
