"""
Test suite for TLS Security Analyzer.

CANARY_STRING_PLACEHOLDER

This file verifies that the analyzer correctly:
- Produces valid JSON output
- Detects export-grade ciphers
- Detects RC4 ciphers
- Detects weak DH parameters
- Validates secure traffic correctly
- Captures session metadata
- Formats cipher suites properly

IMPORTANT: This test suite actually invokes the analyzer on dynamically generated
pcap files to prevent hardcoding solutions.
"""

import json
import subprocess
import sys
import tempfile
import random
import struct
from pathlib import Path

# Generate random canary values at import time
CANARY_IP_OCTET = random.randint(10, 250)
CANARY_PORT = random.randint(50000, 60000)
CANARY_CIPHER = random.choice([0x0006, 0x000B, 0x000E, 0x0011])  # Random export cipher


def make_client_hello(version, ciphers):
    """Build a properly formatted ClientHello with correct lengths"""
    # Build handshake body
    body = struct.pack('>H', version)  # Version
    body += b'\x00' * 32  # Random
    body += b'\x00'  # Session ID length
    body += struct.pack('>H', len(ciphers) * 2)  # Cipher suites length
    for c in ciphers:
        body += struct.pack('>H', c)  # Each cipher suite
    body += b'\x01\x00'  # Compression methods (1 method: null)

    # Build handshake message
    handshake = b'\x01'  # ClientHello type
    handshake += struct.pack('>I', len(body))[1:]  # Length (3 bytes)
    handshake += body

    # Build TLS record
    record = b'\x16'  # Content type: Handshake
    record += struct.pack('>H', version)  # Version
    record += struct.pack('>H', len(handshake))  # Length
    record += handshake

    return record


def make_server_hello(version, cipher):
    """Build a properly formatted ServerHello with correct lengths"""
    # Build handshake body
    body = struct.pack('>H', version)  # Version
    body += b'\x00' * 32  # Random
    body += b'\x00'  # Session ID length
    body += struct.pack('>H', cipher)  # Selected cipher
    body += b'\x00'  # Compression method

    # Build handshake message
    handshake = b'\x02'  # ServerHello type
    handshake += struct.pack('>I', len(body))[1:]  # Length (3 bytes)
    handshake += body

    # Build TLS record
    record = b'\x16'  # Content type: Handshake
    record += struct.pack('>H', version)  # Version
    record += struct.pack('>H', len(handshake))  # Length
    record += handshake

    return record


def make_client_hello_with_groups(version, ciphers, supported_groups):
    """Build ClientHello with supported_groups extension"""
    # Build handshake body
    body = struct.pack('>H', version)  # Version
    body += b'\x00' * 32  # Random
    body += b'\x00'  # Session ID length
    body += struct.pack('>H', len(ciphers) * 2)  # Cipher suites length
    for c in ciphers:
        body += struct.pack('>H', c)  # Each cipher suite
    body += b'\x01\x00'  # Compression methods (1 method: null)

    # Extensions
    extensions = b''
    # supported_groups extension (type 0x000a)
    ext_data = struct.pack('>H', len(supported_groups) * 2)  # Length of list
    for group in supported_groups:
        ext_data += struct.pack('>H', group)
    extensions += struct.pack('>H', 0x000a)  # Extension type
    extensions += struct.pack('>H', len(ext_data))  # Extension length
    extensions += ext_data

    body += struct.pack('>H', len(extensions))  # Extensions length
    body += extensions

    # Build handshake message
    handshake = b'\x01'  # ClientHello type
    handshake += struct.pack('>I', len(body))[1:]  # Length (3 bytes)
    handshake += body

    # Build TLS record
    record = b'\x16'  # Content type: Handshake
    record += struct.pack('>H', version)  # Version
    record += struct.pack('>H', len(handshake))  # Length
    record += handshake

    return record


def make_server_key_exchange_dh(version, prime_size_bits):
    """Build ServerKeyExchange with DH parameters"""
    # Simulate DH params - just need the length field to indicate prime size
    dh_p_len = prime_size_bits // 8  # Prime length in bytes

    # Build handshake body for ServerKeyExchange
    body = b'\x00'  # Curve type or DH params type (0x00 = explicit prime DH)
    body += struct.pack('>H', dh_p_len)  # DH prime length
    body += b'\x00' * min(dh_p_len, 64)  # Dummy DH prime (truncated for brevity)
    body += struct.pack('>H', 1)  # DH generator length
    body += b'\x02'  # Generator
    body += struct.pack('>H', 64)  # DH Ys length
    body += b'\x00' * 64  # Dummy Ys

    # Build handshake message
    handshake = b'\x0c'  # ServerKeyExchange type (12)
    handshake += struct.pack('>I', len(body))[1:]  # Length (3 bytes)
    handshake += body

    # Build TLS record
    record = b'\x16'  # Content type: Handshake
    record += struct.pack('>H', version)  # Version
    record += struct.pack('>H', len(handshake))  # Length
    record += handshake

    return record


def create_test_pcap_raw(packets_data):
    """Create a pcap file from raw TLS records without scapy dependency"""
    try:
        from scapy.all import Ether, IP, TCP, Raw, wrpcap

        packets = []
        for pkt_data in packets_data:
            packets.append(
                Ether() / IP(src=pkt_data['src_ip'], dst=pkt_data['dst_ip']) /
                TCP(sport=pkt_data['src_port'], dport=pkt_data['dst_port'], flags="PA") /
                Raw(load=pkt_data['tls_data'])
            )

        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as f:
            pcap_path = Path(f.name)
            wrpcap(str(pcap_path), packets)
            return pcap_path
    except ImportError:
        # If scapy not available, skip test
        return None


def run_analyzer(pcap_file, method="both"):
    """Run the analyzer on a pcap file and return parsed JSON"""
    result = subprocess.run(
        [sys.executable, "tls_security_analyzer.py", str(pcap_file), "--method", method],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Analyzer failed: {result.stderr}")

    return json.loads(result.stdout)


def test_basic_functionality():
    """Verify the analyzer script executes successfully and produces valid JSON output with required structure.

    This test ensures the analyzer can be invoked, completes without errors, and generates
    valid JSON with the expected top-level fields: analysis_metadata, vulnerability_summary,
    and sessions. It validates metadata and summary fields exist.
    """
    # Create a simple test pcap with export cipher
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.100', 'dst_ip': '93.184.216.34',
            'src_port': 12345, 'dst_port': 443,
            'tls_data': make_client_hello(0x0301, [0x0003, 0x0005])
        },
        {
            'src_ip': '93.184.216.34', 'dst_ip': '192.168.1.100',
            'src_port': 443, 'dst_port': 12345,
            'tls_data': make_server_hello(0x0301, 0x0003)
        }
    ])

    if pcap is None:
        return  # Skip if scapy not available

    try:
        report = run_analyzer(pcap)

        # Check structure
        assert "analysis_metadata" in report
        assert "vulnerability_summary" in report
        assert "sessions" in report

        # Check metadata fields
        assert "total_sessions" in report["analysis_metadata"]
        assert "vulnerable_sessions" in report["analysis_metadata"]
        assert "timestamp" in report["analysis_metadata"]

        # Check summary fields
        assert "export_grade_ciphers" in report["vulnerability_summary"]
        assert "rc4_ciphers" in report["vulnerability_summary"]
        assert "weak_dh_parameters" in report["vulnerability_summary"]
        assert "export_cipher_offered" in report["vulnerability_summary"]
        assert "rc4_cipher_offered" in report["vulnerability_summary"]
    finally:
        pcap.unlink()


def test_vulnerable_detection_export():
    """Verify the analyzer correctly identifies and flags export-grade cipher suites in TLS sessions.

    Export-grade ciphers are legacy weak ciphers. This test validates detection using a randomly
    selected export cipher (canary) to prevent hardcoding.
    """
    # Use randomized export cipher to prevent hardcoding
    pcap = create_test_pcap_raw([
        {
            'src_ip': f'10.0.0.{CANARY_IP_OCTET}', 'dst_ip': '8.8.8.8',
            'src_port': CANARY_PORT, 'dst_port': 443,
            'tls_data': make_client_hello(0x0301, [CANARY_CIPHER, 0x002F])
        },
        {
            'src_ip': '8.8.8.8', 'dst_ip': f'10.0.0.{CANARY_IP_OCTET}',
            'src_port': 443, 'dst_port': CANARY_PORT,
            'tls_data': make_server_hello(0x0301, CANARY_CIPHER)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        # Verify export cipher was detected
        export_count = report["vulnerability_summary"]["export_grade_ciphers"]
        assert export_count > 0, f"Expected export-grade ciphers, found {export_count}"

        # Verify at least one session has export cipher vulnerability
        has_export = any(
            "EXPORT_GRADE_CIPHER" in s.get("vulnerabilities", [])
            for s in report["sessions"]
        )
        assert has_export, "No sessions found with EXPORT_GRADE_CIPHER vulnerability"

        # Anti-hardcoding check: verify canary IP is in the report
        found_canary_ip = any(
            f'10.0.0.{CANARY_IP_OCTET}' in (s['connection']['src_ip'], s['connection']['dst_ip'])
            for s in report['sessions']
        )
        assert found_canary_ip, f"Canary IP 10.0.0.{CANARY_IP_OCTET} not found - analyzer may be hardcoded"

        # Verify the actual cipher ID matches our random canary
        selected_cipher = report['sessions'][0]['cipher_suites']['server_selected']
        assert selected_cipher['id'] == f'0x{CANARY_CIPHER:04X}', \
            f"Expected cipher 0x{CANARY_CIPHER:04X}, got {selected_cipher['id']}"
    finally:
        pcap.unlink()


def test_vulnerable_detection_rc4():
    """Verify the analyzer correctly identifies and flags RC4 cipher suite usage in TLS sessions.

    RC4 is a deprecated stream cipher. This test validates detection.
    """
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.101', 'dst_ip': '172.217.14.206',
            'src_port': 12346, 'dst_port': 443,
            'tls_data': make_client_hello(0x0301, [0x0005, 0x002F])
        },
        {
            'src_ip': '172.217.14.206', 'dst_ip': '192.168.1.101',
            'src_port': 443, 'dst_port': 12346,
            'tls_data': make_server_hello(0x0301, 0x0005)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        rc4_count = report["vulnerability_summary"]["rc4_ciphers"]
        assert rc4_count > 0, f"Expected RC4 ciphers, found {rc4_count}"

        # Verify at least one session has RC4 cipher vulnerability
        has_rc4 = any(
            "RC4_CIPHER" in s.get("vulnerabilities", [])
            for s in report["sessions"]
        )
        assert has_rc4, "No sessions found with RC4_CIPHER vulnerability"
    finally:
        pcap.unlink()


def test_weak_dh_detection():
    """Verify the analyzer correctly identifies weak Diffie-Hellman (DH) parameters in TLS key exchange.

    Weak DH parameters (< 1024 bits) are vulnerable. This test validates actual DH prime extraction
    and detection.
    """
    # Use randomized weak prime size
    weak_prime_size = random.choice([512, 768])

    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.120', 'dst_ip': '203.0.113.1',
            'src_port': 44444, 'dst_port': 443,
            'tls_data': make_client_hello_with_groups(0x0303, [0x0033, 0x0039], [256, 257])
        },
        {
            'src_ip': '203.0.113.1', 'dst_ip': '192.168.1.120',
            'src_port': 443, 'dst_port': 44444,
            'tls_data': make_server_hello(0x0303, 0x0033)
        },
        {
            'src_ip': '203.0.113.1', 'dst_ip': '192.168.1.120',
            'src_port': 443, 'dst_port': 44444,
            'tls_data': make_server_key_exchange_dh(0x0303, weak_prime_size)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        # Find session with DH parameters
        session = report['sessions'][0]
        dh_info = session.get('diffie_hellman', {})
        prime_size = dh_info.get('prime_size_bits')

        assert prime_size is not None, "DH prime size not extracted"
        assert prime_size == weak_prime_size, \
            f"Expected prime size {weak_prime_size}, got {prime_size}"

        # Should be flagged as weak
        vulnerabilities = session.get('vulnerabilities', [])
        assert 'WEAK_DH_PARAMETERS' in vulnerabilities, \
            f"DH prime {prime_size} bits should be flagged as WEAK_DH_PARAMETERS"

        # Verify summary counter
        weak_dh_count = report['vulnerability_summary']['weak_dh_parameters']
        assert weak_dh_count == 1, f"Expected 1 weak DH session, got {weak_dh_count}"
    finally:
        pcap.unlink()


def test_secure_traffic_validation():
    """Verify the analyzer correctly identifies secure TLS traffic without false positives.

    This test ensures modern TLS 1.3 configurations are correctly reported as secure.
    """
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.200', 'dst_ip': '1.1.1.1',
            'src_port': 54321, 'dst_port': 443,
            'tls_data': make_client_hello(0x0303, [0x1301, 0x1302, 0x1303])
        },
        {
            'src_ip': '1.1.1.1', 'dst_ip': '192.168.1.200',
            'src_port': 443, 'dst_port': 54321,
            'tls_data': make_server_hello(0x0303, 0x1301)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        vuln_count = report["analysis_metadata"]["vulnerable_sessions"]
        assert vuln_count == 0, f"Secure pcap should have 0 vulnerabilities, found {vuln_count}"
    finally:
        pcap.unlink()


def test_offered_vs_selected_vulnerabilities():
    """Verify the analyzer distinguishes between offered and selected vulnerability flags.

    Tests EXPORT_CIPHER_OFFERED vs EXPORT_GRADE_CIPHER and RC4_CIPHER_OFFERED vs RC4_CIPHER.
    """
    # Client offers export but server selects secure cipher
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.150', 'dst_ip': '1.1.1.1',
            'src_port': 55555, 'dst_port': 443,
            'tls_data': make_client_hello(0x0303, [0x0003, 0x1301, 0x1302])
        },
        {
            'src_ip': '1.1.1.1', 'dst_ip': '192.168.1.150',
            'src_port': 443, 'dst_port': 55555,
            'tls_data': make_server_hello(0x0303, 0x1301)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        session = report['sessions'][0]
        vulns = session.get('vulnerabilities', [])

        # Should have EXPORT_CIPHER_OFFERED but NOT EXPORT_GRADE_CIPHER
        assert 'EXPORT_CIPHER_OFFERED' in vulns, "Should detect export cipher was offered"
        assert 'EXPORT_GRADE_CIPHER' not in vulns, "Should NOT detect export cipher selected"

        # Verify summary counters
        assert report['vulnerability_summary']['export_cipher_offered'] == 1
        assert report['vulnerability_summary']['export_grade_ciphers'] == 0
    finally:
        pcap.unlink()


def test_supported_groups_content():
    """Verify the analyzer populates supported_groups and named_groups with actual data.

    Validates extraction of supported_groups extension from ClientHello.
    """
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.120', 'dst_ip': '203.0.113.1',
            'src_port': 44444, 'dst_port': 443,
            'tls_data': make_client_hello_with_groups(0x0303, [0x0033], [256, 257, 258])
        },
        {
            'src_ip': '203.0.113.1', 'dst_ip': '192.168.1.120',
            'src_port': 443, 'dst_port': 44444,
            'tls_data': make_server_hello(0x0303, 0x0033)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        session = report['sessions'][0]
        dh_info = session.get('diffie_hellman', {})
        supported_groups = dh_info.get('supported_groups', [])
        named_groups = dh_info.get('named_groups', [])

        assert supported_groups == [256, 257, 258], \
            f"Expected groups [256, 257, 258], got {supported_groups}"

        # Verify named_groups has correct names
        assert len(named_groups) == 3
        assert named_groups[0] == "ffdhe2048"
        assert named_groups[1] == "ffdhe3072"
        assert named_groups[2] == "ffdhe4096"
    finally:
        pcap.unlink()


def test_timestamp_unix_field():
    """Verify the analyzer includes Unix epoch timestamp in each session.

    Validates both timestamp (ISO 8601) and timestamp_unix (epoch) fields.
    """
    pcap = create_test_pcap_raw([
        {
            'src_ip': '192.168.1.100', 'dst_ip': '93.184.216.34',
            'src_port': 12345, 'dst_port': 443,
            'tls_data': make_client_hello(0x0301, [0x1301])
        },
        {
            'src_ip': '93.184.216.34', 'dst_ip': '192.168.1.100',
            'src_port': 443, 'dst_port': 12345,
            'tls_data': make_server_hello(0x0301, 0x1301)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        session = report['sessions'][0]

        # Check both timestamp fields exist
        assert "timestamp" in session, "Missing ISO timestamp"
        assert "timestamp_unix" in session, "Missing Unix epoch timestamp"

        # Validate timestamp_unix is a number
        assert isinstance(session["timestamp_unix"], (int, float)), \
            f"timestamp_unix should be numeric, got {type(session['timestamp_unix'])}"

        # Validate it's a reasonable timestamp (after 2000, before 2100)
        ts = session["timestamp_unix"]
        assert 946684800 < ts < 4102444800, \
            f"timestamp_unix {ts} is not a valid Unix timestamp"
    finally:
        pcap.unlink()


def test_multiple_sessions_handling():
    """Verify the analyzer correctly handles pcap files with multiple TLS sessions.

    Validates distinct session tracking and proper vulnerability assignment.
    """
    # Create 3 sessions with different IPs
    random_port_1 = random.randint(50000, 51000)
    random_port_2 = random.randint(51000, 52000)
    random_port_3 = random.randint(52000, 53000)

    pcap = create_test_pcap_raw([
        # Session 1: Export cipher
        {'src_ip': '192.168.1.100', 'dst_ip': '93.184.216.34',
         'src_port': random_port_1, 'dst_port': 443,
         'tls_data': make_client_hello(0x0301, [0x0003])},
        {'src_ip': '93.184.216.34', 'dst_ip': '192.168.1.100',
         'src_port': 443, 'dst_port': random_port_1,
         'tls_data': make_server_hello(0x0301, 0x0003)},

        # Session 2: RC4 cipher
        {'src_ip': '192.168.1.101', 'dst_ip': '172.217.14.206',
         'src_port': random_port_2, 'dst_port': 443,
         'tls_data': make_client_hello(0x0301, [0x0005])},
        {'src_ip': '172.217.14.206', 'dst_ip': '192.168.1.101',
         'src_port': 443, 'dst_port': random_port_2,
         'tls_data': make_server_hello(0x0301, 0x0005)},

        # Session 3: Secure
        {'src_ip': '192.168.1.102', 'dst_ip': '1.1.1.1',
         'src_port': random_port_3, 'dst_port': 443,
         'tls_data': make_client_hello(0x0303, [0x1301])},
        {'src_ip': '1.1.1.1', 'dst_ip': '192.168.1.102',
         'src_port': 443, 'dst_port': random_port_3,
         'tls_data': make_server_hello(0x0303, 0x1301)},
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        total_sessions = report["analysis_metadata"]["total_sessions"]
        assert total_sessions == 3, f"Expected 3 sessions, found {total_sessions}"

        # Verify sessions have distinct identifiers
        session_ids = [s["session_id"] for s in report["sessions"]]
        assert len(session_ids) == len(set(session_ids)), "Session IDs should be unique"

        # Verify different vulnerabilities
        vuln_sets = [tuple(sorted(s.get("vulnerabilities", []))) for s in report["sessions"]]
        assert len(set(vuln_sets)) == 3, "Sessions should have different vulnerability profiles"

        # Verify canary ports are present (anti-hardcoding)
        found_ports = {s['connection']['src_port'] for s in report['sessions']}
        found_ports.update({s['connection']['dst_port'] for s in report['sessions']})
        assert random_port_1 in found_ports, f"Canary port {random_port_1} not found"
    finally:
        pcap.unlink()


def test_cli_backend_selection():
    """Verify CLI options for backend selection (--method tshark/scapy/both).

    Validates --method flag is respected and appropriate error messages.
    """
    pcap = create_test_pcap_raw([
        {'src_ip': '192.168.1.100', 'dst_ip': '93.184.216.34',
         'src_port': 12345, 'dst_port': 443,
         'tls_data': make_client_hello(0x0301, [0x1301])},
        {'src_ip': '93.184.216.34', 'dst_ip': '192.168.1.100',
         'src_port': 443, 'dst_port': 12345,
         'tls_data': make_server_hello(0x0301, 0x1301)},
    ])

    if pcap is None:
        return

    try:
        # Test scapy backend (should work)
        result = subprocess.run(
            [sys.executable, "tls_security_analyzer.py", str(pcap), "--method", "scapy"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Scapy backend should work"

        # Test both backend
        result = subprocess.run(
            [sys.executable, "tls_security_analyzer.py", str(pcap), "--method", "both"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Both backend should work"

        # Test invalid method gives error
        result = subprocess.run(
            [sys.executable, "tls_security_analyzer.py", str(pcap), "--method", "invalid"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Invalid method should fail"
        assert "invalid choice" in result.stderr.lower(), "Should report invalid choice"
    finally:
        pcap.unlink()


def test_malformed_packet_handling():
    """Verify the analyzer handles malformed packets gracefully without crashing.

    Tests robustness with truncated and corrupted TLS records.
    """
    # Mix valid and malformed data
    valid_ch = make_client_hello(0x0303, [0x1301])
    valid_sh = make_server_hello(0x0303, 0x1301)
    malformed = b'\x16\x03\x03\x00\x64' + b'\x01\x00\x00\x10'  # Truncated

    pcap = create_test_pcap_raw([
        {'src_ip': '192.168.1.130', 'dst_ip': '1.1.1.1',
         'src_port': 55555, 'dst_port': 443,
         'tls_data': valid_ch},
        {'src_ip': '1.1.1.1', 'dst_ip': '192.168.1.130',
         'src_port': 443, 'dst_port': 55555,
         'tls_data': valid_sh},
        {'src_ip': '192.168.1.131', 'dst_ip': '1.1.1.1',
         'src_port': 55556, 'dst_port': 443,
         'tls_data': malformed},
    ])

    if pcap is None:
        return

    try:
        # Should not crash - graceful handling
        report = run_analyzer(pcap)

        # Should have valid structure even with malformed packets
        assert "analysis_metadata" in report
        assert "sessions" in report
        assert isinstance(report["sessions"], list)

        # Should have at least the valid session
        assert len(report["sessions"]) >= 1
    finally:
        pcap.unlink()


def test_anti_hardcoding():
    """Verify the analyzer actually parses pcap files rather than using hardcoded responses.

    Uses randomized canary values that change each test run to prevent hardcoding solutions.
    """
    # Generate unique canary values
    canary_ip = f'10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}'
    canary_port = random.randint(40000, 65000)
    canary_cipher = random.choice(list(range(0x0003, 0x0020)))  # Random cipher

    pcap = create_test_pcap_raw([
        {
            'src_ip': canary_ip, 'dst_ip': '8.8.8.8',
            'src_port': canary_port, 'dst_port': 443,
            'tls_data': make_client_hello(0x0301, [canary_cipher])
        },
        {
            'src_ip': '8.8.8.8', 'dst_ip': canary_ip,
            'src_port': 443, 'dst_port': canary_port,
            'tls_data': make_server_hello(0x0301, canary_cipher)
        }
    ])

    if pcap is None:
        return

    try:
        report = run_analyzer(pcap)

        sessions = report["sessions"]
        assert len(sessions) > 0, "No sessions found"

        # Verify canary IP is in the report (proves actual parsing)
        found_canary_ip = any(
            canary_ip in (s['connection']['src_ip'], s['connection']['dst_ip'])
            for s in sessions
        )
        assert found_canary_ip, \
            f"Canary IP {canary_ip} not found in {sessions}. Analyzer may be hardcoded."

        # Verify canary port is in the report
        found_canary_port = any(
            canary_port in (s['connection']['src_port'], s['connection']['dst_port'])
            for s in sessions
        )
        assert found_canary_port, \
            f"Canary port {canary_port} not found. Analyzer may be hardcoded."

        # Verify cipher matches
        selected = sessions[0]['cipher_suites']['server_selected']
        assert selected['id'] == f'0x{canary_cipher:04X}', \
            f"Expected cipher 0x{canary_cipher:04X}, got {selected['id']}. Analyzer may be hardcoded."
    finally:
        pcap.unlink()
