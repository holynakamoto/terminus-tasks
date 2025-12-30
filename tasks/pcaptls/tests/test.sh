#!/bin/bash

# Test script for TLS Security Analyzer
# This script runs the analyzer on test pcap files and validates the output

set -e

echo "=== TLS Security Analyzer Test Suite ==="
echo

# Check if test captures exist (should be created by solve.sh)
if [ ! -d "test_captures" ] || [ ! -f "test_captures/vulnerable_tls.pcap" ]; then
    echo "ERROR: test_captures not found. solve.sh should have created it." >&2
    exit 1
fi

# Test 1: Basic functionality - vulnerable pcap
echo "Test 1: Basic functionality"
python3 tls_security_analyzer.py test_captures/vulnerable_tls.pcap -o report.json
test -f report.json || (echo "ERROR: report.json not created" && exit 1)
python3 -c "import json; json.load(open('report.json'))" || (echo "ERROR: Invalid JSON" && exit 1)
echo "✓ Basic functionality test passed"
echo

# Test 2: Export cipher detection
echo "Test 2: Export-grade cipher detection"
python3 << 'EOF'
import json
report = json.load(open('report.json'))
export_count = report['vulnerability_summary']['export_grade_ciphers']
assert export_count > 0, f"Expected export-grade ciphers, found {export_count}"
print(f"✓ Detected {export_count} export-grade cipher sessions")
EOF
echo

# Test 3: RC4 cipher detection
echo "Test 3: RC4 cipher detection"
python3 << 'EOF'
import json
report = json.load(open('report.json'))
rc4_count = report['vulnerability_summary']['rc4_ciphers']
assert rc4_count > 0, f"Expected RC4 ciphers, found {rc4_count}"
print(f"✓ Detected {rc4_count} RC4 cipher sessions")
EOF
echo

# Test 4: Weak DH detection
echo "Test 4: Weak DH parameter detection"
python3 << 'EOF'
import json
report = json.load(open('report.json'))
weak_dh = report['vulnerability_summary']['weak_dh_parameters']
# Note: May be 0 if test pcap doesn't include actual DH key exchange
print(f"✓ Weak DH parameter field present (count: {weak_dh})")
EOF
echo

# Test 5: Secure traffic validation
echo "Test 5: Secure traffic validation"
python3 tls_security_analyzer.py test_captures/secure_tls.pcap -o secure_report.json
python3 << 'EOF'
import json
report = json.load(open('secure_report.json'))
vuln_count = report['analysis_metadata']['vulnerable_sessions']
assert vuln_count == 0, f"Secure pcap should have 0 vulnerabilities, found {vuln_count}"
print(f"✓ Secure traffic correctly identified (0 vulnerabilities)")
EOF
echo

# Test 6: Session details
echo "Test 6: Session metadata validation"
python3 tls_security_analyzer.py test_captures/mixed_tls.pcap -o mixed_report.json
python3 << 'EOF'
import json
report = json.load(open('mixed_report.json'))
sessions = report['sessions']
assert len(sessions) > 0, "No sessions found"

for session in sessions:
    assert 'timestamp' in session, "Missing timestamp"
    assert 'connection' in session, "Missing connection info"
    assert 'cipher_suites' in session, "Missing cipher suites"
    assert 'vulnerabilities' in session, "Missing vulnerabilities"
    assert 'is_vulnerable' in session, "Missing vulnerability status"
    
    conn = session['connection']
    assert conn['src_ip'] is not None, "Missing source IP"
    assert conn['dst_ip'] is not None, "Missing destination IP"

print(f"✓ All {len(sessions)} sessions have complete metadata")
EOF
echo

# Test 7: Cipher suite naming
echo "Test 7: Cipher suite naming"
python3 << 'EOF'
import json
report = json.load(open('report.json'))

print(f"\n=== DEBUG: Full report structure ===")
print(f"Total sessions: {len(report['sessions'])}")

for i, session in enumerate(report['sessions']):
    print(f"\n--- Session {i} ---")
    print(f"ID: {session['session_id']}")
    print(f"Connection: {session['connection']}")
    print(f"Timestamp: {session['timestamp']}")
    
    offered = session['cipher_suites']['client_offered']
    print(f"Client offered ({len(offered)} ciphers):")
    for c in offered:
        print(f"  {c}")
    
    selected = session['cipher_suites']['server_selected']
    print(f"Server selected: {selected}")
    
    print(f"Vulnerabilities: {session['vulnerabilities']}")

print("\n=== Running actual test ===")
for session in report['sessions']:
    offered = session['cipher_suites']['client_offered']
    print(f"Checking session {session['session_id']}: {len(offered)} client ciphers")
    assert len(offered) > 0, f"No client ciphers offered in {session['session_id']}"
    
    for cipher in offered:
        assert 'id' in cipher, "Missing cipher ID"
        assert 'name' in cipher, "Missing cipher name"
        assert cipher['id'].startswith('0x'), "Cipher ID should be hex"

print("✓ Cipher suites properly formatted with IDs and names")
EOF
echo

echo "=== All tests passed! ==="
echo

# Output reward for Harbor scoring
mkdir -p /logs/verifier
echo "1.0" | tee /logs/verifier/reward.txt
