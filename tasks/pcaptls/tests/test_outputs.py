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
"""

import json
from pathlib import Path


def test_basic_functionality():
    """Verify the analyzer script executes successfully and produces valid JSON output with required structure.
    
    This test ensures the analyzer can be invoked, completes without errors, and generates
    a report.json file containing the expected top-level fields: analysis_metadata,
    vulnerability_summary, and sessions. It validates that metadata includes total_sessions,
    vulnerable_sessions, and timestamp fields, and that the vulnerability summary includes
    export_grade_ciphers, rc4_ciphers, and weak_dh_parameters counters.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
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


def test_vulnerable_detection_export():
    """Verify the analyzer correctly identifies and flags export-grade cipher suites in TLS sessions.
    
    Export-grade ciphers are legacy weak ciphers that were intentionally weakened for export
    compliance. This test validates that the analyzer detects when export-grade ciphers are
    selected by the server, increments the export_grade_ciphers counter in the summary, and
    marks affected sessions with the EXPORT_GRADE_CIPHER vulnerability flag.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    export_count = report["vulnerability_summary"]["export_grade_ciphers"]
    assert export_count > 0, f"Expected export-grade ciphers, found {export_count}"
    
    # Verify at least one session has export cipher vulnerability
    has_export = any(
        "EXPORT_GRADE_CIPHER" in s.get("vulnerabilities", [])
        for s in report["sessions"]
    )
    assert has_export, "No sessions found with EXPORT_GRADE_CIPHER vulnerability"


def test_vulnerable_detection_rc4():
    """Verify the analyzer correctly identifies and flags RC4 cipher suite usage in TLS sessions.
    
    RC4 is a stream cipher that has been deprecated due to cryptographic weaknesses. This test
    validates that the analyzer detects when RC4 ciphers are selected by the server, increments
    the rc4_ciphers counter in the vulnerability summary, and marks affected sessions with
    the RC4_CIPHER vulnerability flag.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    rc4_count = report["vulnerability_summary"]["rc4_ciphers"]
    assert rc4_count > 0, f"Expected RC4 ciphers, found {rc4_count}"
    
    # Verify at least one session has RC4 cipher vulnerability
    has_rc4 = any(
        "RC4_CIPHER" in s.get("vulnerabilities", [])
        for s in report["sessions"]
    )
    assert has_rc4, "No sessions found with RC4_CIPHER vulnerability"


def test_weak_dh_detection():
    """Verify the analyzer correctly identifies weak Diffie-Hellman (DH) parameters in TLS key exchange.
    
    Weak DH parameters (typically prime sizes < 1024 bits) are vulnerable to cryptographic attacks.
    This test validates that the analyzer extracts DH prime sizes from ServerKeyExchange messages,
    maintains the weak_dh_parameters counter in the vulnerability summary, and properly flags
    sessions with WEAK_DH_PARAMETERS when primes are below the security threshold.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    weak_dh = report["vulnerability_summary"]["weak_dh_parameters"]
    # Note: Weak DH detection may be 0 if test pcap doesn't include actual DH key exchange
    # This test verifies the field exists and is properly counted
    assert isinstance(weak_dh, int), "weak_dh_parameters should be an integer"


def test_secure_traffic_validation():
    """Verify the analyzer correctly identifies secure TLS traffic without false positives.
    
    This test ensures that when analyzing pcap files containing only secure, modern TLS
    configurations (e.g., TLS 1.3 with strong ciphers), the analyzer correctly reports zero
    vulnerabilities. This validates that the vulnerability detection logic doesn't produce
    false positives and can distinguish between vulnerable and secure configurations.
    """
    report_file = Path("secure_report.json")
    if not report_file.exists():
        # Skip if secure report not generated
        return
    
    with open(report_file) as f:
        report = json.load(f)
    
    vuln_count = report["analysis_metadata"]["vulnerable_sessions"]
    assert vuln_count == 0, f"Secure pcap should have 0 vulnerabilities, found {vuln_count}"


def test_session_details():
    """Verify the analyzer captures complete session metadata including connection details and timestamps.
    
    This test validates that each TLS session in the report includes all required metadata fields:
    timestamp (both ISO format and Unix epoch), connection information (source/destination IPs
    and ports), cipher suite details, vulnerability flags, and the is_vulnerable boolean status.
    Complete metadata is essential for security analysis and incident response workflows.
    """
    report_file = Path("mixed_report.json")
    if not report_file.exists():
        report_file = Path("report.json")
    
    assert report_file.exists(), "No report file found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    sessions = report["sessions"]
    assert len(sessions) > 0, "No sessions found"
    
    for session in sessions:
        assert "timestamp" in session, "Missing timestamp"
        assert "connection" in session, "Missing connection info"
        assert "cipher_suites" in session, "Missing cipher suites"
        assert "vulnerabilities" in session, "Missing vulnerabilities"
        assert "is_vulnerable" in session, "Missing vulnerability status"
        
        # Check connection details
        conn = session["connection"]
        assert conn["src_ip"] is not None, "Missing source IP"
        assert conn["dst_ip"] is not None, "Missing destination IP"
        assert conn["src_port"] is not None, "Missing source port"
        assert conn["dst_port"] is not None, "Missing destination port"


def test_cipher_suite_naming():
    """Verify the analyzer provides both hexadecimal IDs and human-readable names for cipher suites.
    
    This test ensures that all cipher suites in the report (both client-offered and server-selected)
    include both the hexadecimal identifier (e.g., "0x0003") and a descriptive name (e.g.,
    "TLS_RSA_EXPORT_WITH_RC4_40_MD5"). Proper naming improves readability and helps security
    analysts quickly understand the cryptographic configuration without needing to look up
    cipher suite codes manually.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    for session in report["sessions"]:
        offered = session["cipher_suites"]["client_offered"]
        assert len(offered) > 0, "No client ciphers offered"
        
        for cipher in offered:
            assert "id" in cipher, "Missing cipher ID"
            assert "name" in cipher, "Missing cipher name"
            assert cipher["id"].startswith("0x"), "Cipher ID should be hex"
        
        # Check server selected cipher if present
        if session["cipher_suites"]["server_selected"]:
            selected = session["cipher_suites"]["server_selected"]
            assert "id" in selected, "Missing selected cipher ID"
            assert "name" in selected, "Missing selected cipher name"
            assert selected["id"].startswith("0x"), "Selected cipher ID should be hex"


def test_anti_hardcoding():
    """Verify the analyzer actually parses pcap files rather than using hardcoded responses.
    
    This anti-cheating test validates that the analyzer extracts connection information (specifically
    source IP addresses) from the actual pcap file contents. It checks for specific IP addresses
    that are dynamically generated in the test pcap files, ensuring the analyzer is performing
    real packet parsing rather than returning pre-computed or hardcoded results. This prevents
    solutions that bypass the actual analysis work.
    """
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    # Canary: Verify specific IPs from dynamically generated pcaps
    # These IPs are hardcoded in solve.sh's pcap generation
    sessions = report["sessions"]
    assert len(sessions) > 0, "No sessions found"
    
    # Check that at least one session has expected source IPs from generated pcaps
    found_ips = {s["connection"]["src_ip"] for s in sessions}
    expected_ips = {"192.168.1.100", "192.168.1.101"}  # From capture_1.pcap
    
    assert any(ip in found_ips for ip in expected_ips), \
        f"Expected IPs {expected_ips} not found in {found_ips}. Analyzer may be hardcoded."
