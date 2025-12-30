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

# Test 8: Offered vs Selected Cipher Distinction
echo "Test 8: Offered vs Selected Cipher Distinction"
python3 << 'EOF'
import json
report = json.load(open('report.json'))

# Verify the distinction between offered and selected vulnerabilities
export_offered = report['vulnerability_summary'].get('export_cipher_offered', 0)
export_selected = report['vulnerability_summary']['export_grade_ciphers']
rc4_offered = report['vulnerability_summary'].get('rc4_cipher_offered', 0)
rc4_selected = report['vulnerability_summary']['rc4_ciphers']

print(f"Export ciphers - Offered: {export_offered}, Selected: {export_selected}")
print(f"RC4 ciphers - Offered: {rc4_offered}, Selected: {rc4_selected}")

# Verify at session level
for session in report['sessions']:
    vulnerabilities = session['vulnerabilities']
    offered_ciphers = session['cipher_suites']['client_offered']
    selected_cipher = session['cipher_suites']['server_selected']

    # Check if EXPORT_CIPHER_OFFERED is properly detected
    has_export_offered = any(
        vuln == 'EXPORT_CIPHER_OFFERED' for vuln in vulnerabilities
    )
    has_export_selected = any(
        vuln == 'EXPORT_GRADE_CIPHER' for vuln in vulnerabilities
    )

    # If server selected export cipher, both flags should be present
    if has_export_selected:
        assert has_export_offered, f"Session {session['session_id']}: Selected export but didn't mark as offered"

    # Similar check for RC4
    has_rc4_offered = any(
        vuln == 'RC4_CIPHER_OFFERED' for vuln in vulnerabilities
    )
    has_rc4_selected = any(
        vuln == 'RC4_CIPHER' for vuln in vulnerabilities
    )

    if has_rc4_selected:
        assert has_rc4_offered, f"Session {session['session_id']}: Selected RC4 but didn't mark as offered"

print("✓ Offered vs selected cipher distinction working correctly")
EOF
echo

# Test 9: Offered-not-selected behavior
echo "Test 9: Offered-not-selected behavior"
python3 tls_security_analyzer.py test_captures/offered_not_selected.pcap -o offered_report.json
python3 << 'EOF'
import json
report = json.load(open('offered_report.json'))

# Should have 1 session where export is offered but not selected
assert len(report['sessions']) == 1, "Expected 1 session"
session = report['sessions'][0]

# Should have EXPORT_CIPHER_OFFERED but NOT EXPORT_GRADE_CIPHER
vulnerabilities = session['vulnerabilities']
assert 'EXPORT_CIPHER_OFFERED' in vulnerabilities, "Should detect export cipher was offered"
assert 'EXPORT_GRADE_CIPHER' not in vulnerabilities, "Should NOT detect export cipher selected"

# Verify counts
assert report['vulnerability_summary']['export_cipher_offered'] == 1, "Should count 1 offered"
assert report['vulnerability_summary']['export_grade_ciphers'] == 0, "Should count 0 selected"

print("✓ Offered-not-selected distinction works correctly")
EOF
echo

# Test 10: Multiple export ciphers
echo "Test 10: Multiple export cipher types"
python3 tls_security_analyzer.py test_captures/multiple_export.pcap -o multi_export_report.json
python3 << 'EOF'
import json
report = json.load(open('multi_export_report.json'))

assert len(report['sessions']) == 1, "Expected 1 session"
session = report['sessions'][0]

# Verify different export cipher (0x0006) is detected
selected = session['cipher_suites']['server_selected']
assert selected['id'] == '0x0006', f"Expected cipher 0x0006, got {selected['id']}"
assert 'EXPORT' in selected['name'].upper(), "Cipher name should indicate export"

# Should detect export vulnerability
assert 'EXPORT_GRADE_CIPHER' in session['vulnerabilities'], "Should detect export cipher"

print("✓ Multiple export cipher types detected correctly")
EOF
echo

# Test 11: RC4-only (no export)
echo "Test 11: RC4 cipher without export"
python3 tls_security_analyzer.py test_captures/rc4_only.pcap -o rc4_report.json
python3 << 'EOF'
import json
report = json.load(open('rc4_report.json'))

assert len(report['sessions']) == 1, "Expected 1 session"
session = report['sessions'][0]

# Should detect RC4 but not export
assert 'RC4_CIPHER' in session['vulnerabilities'], "Should detect RC4 cipher"
assert 'EXPORT_GRADE_CIPHER' not in session['vulnerabilities'], "Should NOT detect export"

# Verify RC4 count but not export count
assert report['vulnerability_summary']['rc4_ciphers'] == 1, "Should count 1 RC4 cipher"
assert report['vulnerability_summary']['export_grade_ciphers'] == 0, "Should count 0 export ciphers"

print("✓ RC4-only detection works correctly")
EOF
echo

# Test 12: Backend selection (tshark/scapy)
echo "Test 12: Backend selection and fallback"
python3 << 'EOF'
import subprocess
import json
import os

# Test with explicit tshark backend (if available)
tshark_available = subprocess.run(['which', 'tshark'], capture_output=True).returncode == 0
scapy_available = True  # scapy is in requirements

if tshark_available:
    print("Testing with tshark backend...")
    result = subprocess.run(
        ['python3', 'tls_security_analyzer.py', 'test_captures/vulnerable_tls.pcap', '-m', 'tshark', '-o', 'tshark_report.json'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        with open('tshark_report.json') as f:
            report = json.load(f)
        assert len(report['sessions']) > 0, "tshark backend produced no sessions"
        print(f"  ✓ tshark backend works ({len(report['sessions'])} sessions)")
    else:
        print(f"  ⚠ tshark backend failed: {result.stderr}")
else:
    print("  ⚠ tshark not available, skipping tshark test")

# Test with explicit scapy backend
print("Testing with scapy backend...")
result = subprocess.run(
    ['python3', 'tls_security_analyzer.py', 'test_captures/vulnerable_tls.pcap', '-m', 'scapy', '-o', 'scapy_report.json'],
    capture_output=True, text=True
)
if result.returncode == 0:
    with open('scapy_report.json') as f:
        report = json.load(f)
    assert len(report['sessions']) > 0, "scapy backend produced no sessions"
    print(f"  ✓ scapy backend works ({len(report['sessions'])} sessions)")
else:
    print(f"  ✗ scapy backend failed: {result.stderr}")
    raise AssertionError("scapy backend should be available and working")

# Test auto-selection (no -m flag)
print("Testing auto backend selection...")
result = subprocess.run(
    ['python3', 'tls_security_analyzer.py', 'test_captures/vulnerable_tls.pcap', '-o', 'auto_report.json'],
    capture_output=True, text=True
)
assert result.returncode == 0, f"Auto backend selection failed: {result.stderr}"
with open('auto_report.json') as f:
    report = json.load(f)
assert len(report['sessions']) > 0, "Auto backend produced no sessions"
print(f"  ✓ Auto backend selection works ({len(report['sessions'])} sessions)")

print("✓ Backend selection and fallback working correctly")
EOF
echo

# Test 13: DH parameter extraction
echo "Test 13: DH parameter extraction"
python3 tls_security_analyzer.py test_captures/weak_dh.pcap -o dh_report.json
python3 << 'EOF'
import json
report = json.load(open('dh_report.json'))

assert len(report['sessions']) == 1, "Expected 1 session"
session = report['sessions'][0]

# Check that DH information is present
dh_info = session.get('diffie_hellman', {})
assert dh_info is not None, "DH information should be present"

# Verify supported_groups field exists (even if empty)
assert 'supported_groups' in dh_info or 'named_groups' in dh_info, "DH groups should be extracted"

print(f"  DH info extracted: {dh_info}")
print("✓ DH parameter extraction working")
EOF
echo

echo "=== All tests passed! ==="
echo

# Output reward for Harbor scoring
mkdir -p /logs/verifier
echo "1.0" | tee /logs/verifier/reward.txt
