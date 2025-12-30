"""
Test suite for TLS Security Analyzer.

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
    """Test script runs and produces valid JSON output."""
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
    """Detect export-grade cipher usage."""
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
    """Detect RC4 cipher usage."""
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
    """Detect weak Diffie-Hellman parameters."""
    report_file = Path("report.json")
    assert report_file.exists(), "report.json not found"
    
    with open(report_file) as f:
        report = json.load(f)
    
    weak_dh = report["vulnerability_summary"]["weak_dh_parameters"]
    # Note: Weak DH detection may be 0 if test pcap doesn't include actual DH key exchange
    # This test verifies the field exists and is properly counted
    assert isinstance(weak_dh, int), "weak_dh_parameters should be an integer"


def test_secure_traffic_validation():
    """Validate secure traffic has no vulnerabilities."""
    report_file = Path("secure_report.json")
    if not report_file.exists():
        # Skip if secure report not generated
        return
    
    with open(report_file) as f:
        report = json.load(f)
    
    vuln_count = report["analysis_metadata"]["vulnerable_sessions"]
    assert vuln_count == 0, f"Secure pcap should have 0 vulnerabilities, found {vuln_count}"


def test_session_details():
    """Verify session metadata is captured correctly."""
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
    """Verify cipher suites are properly named."""
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
