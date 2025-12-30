#!/bin/bash

# Solution script for TLS Security Analyzer task
# This script generates test pcap files and runs the analyzer

set -e

echo "=== TLS Security Analyzer Solution ==="
echo

# Workaround for debug environment - copy from mounted location if available
# In real Harbor environment, files are copied to /app by Harbor from [task.files]
if [ ! -f "tls_security_analyzer.py" ]; then
    if [ -f "/task_source/tls_security_analyzer.py" ]; then
        echo "Copying tls_security_analyzer.py from /task_source (debug environment workaround)..."
        cp /task_source/tls_security_analyzer.py /app/
    else
        echo "Error: tls_security_analyzer.py not found in /app or /task_source" >&2
        echo "This file should be copied by Harbor from [task.files] in task.toml" >&2
        exit 1
    fi
fi

# Make sure it's executable (ignore errors if file is read-only)
chmod +x tls_security_analyzer.py 2>/dev/null || true

# Generate test pcap files - always regenerate for testing
echo "Generating test pcap files..."
rm -rf test_captures  # Force regeneration
python3 << 'EOFPYTHON'
#!/usr/bin/env python3
"""
Generate test pcap files for TLS Security Analyzer
Creates synthetic TLS handshake captures with various security configurations
"""

import os
from scapy.all import *

def create_test_captures():
    """Generate test pcap files with different TLS configurations"""
    import struct

    os.makedirs("test_captures", exist_ok=True)

    print("Generating test pcap files...")
    print()

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

    # 1. Vulnerable session with export cipher
    print("Generating vulnerable_tls.pcap...")

    try:
        vulnerable_packets = []

        # Session 1: Export cipher (0x0003)
        ch1_data = make_client_hello(0x0301, [0x0003, 0x0005])  # TLS 1.0
        vulnerable_packets.append(Ether()/IP(src="192.168.1.100", dst="93.184.216.34")/TCP(sport=12345, dport=443, flags="PA")/Raw(load=ch1_data))

        sh1_data = make_server_hello(0x0301, 0x0003)  # Export cipher
        vulnerable_packets.append(Ether()/IP(src="93.184.216.34", dst="192.168.1.100")/TCP(sport=443, dport=12345, flags="PA")/Raw(load=sh1_data))

        # Session 2: RC4 cipher (0x0005)
        ch2_data = make_client_hello(0x0301, [0x0005, 0x002f])  # TLS 1.0
        vulnerable_packets.append(Ether()/IP(src="192.168.1.101", dst="172.217.14.206")/TCP(sport=12346, dport=443, flags="PA")/Raw(load=ch2_data))

        sh2_data = make_server_hello(0x0301, 0x0005)  # RC4 cipher
        vulnerable_packets.append(Ether()/IP(src="172.217.14.206", dst="192.168.1.101")/TCP(sport=443, dport=12346, flags="PA")/Raw(load=sh2_data))
        
        # Verify all packets have Raw layers
        for i, p in enumerate(vulnerable_packets):
            if not p.haslayer(Raw):
                print(f"  ERROR: Packet {i} missing Raw layer!", file=sys.stderr)
            else:
                raw_len = len(p[Raw].load)
                first_byte = p[Raw].load[0] if len(p[Raw].load) > 0 else 0
                hs_type = p[Raw].load[5] if len(p[Raw].load) > 5 else 0
                hs_name = {1: 'ClientHello', 2: 'ServerHello'}.get(hs_type, 'Unknown')
                print(f"  DEBUG: Packet {i}: Raw len={raw_len}, first=0x{first_byte:02x}, hs_type={hs_type} ({hs_name})", file=sys.stderr)
        
        wrpcap("test_captures/vulnerable_tls.pcap", vulnerable_packets)
        print("  ✓ Created vulnerable_tls.pcap with export and RC4 ciphers")
        print()
        
    except Exception as e:
        print(f"  Error creating vulnerable pcap: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Secure session
    print("Generating secure_tls.pcap...")
    try:
        secure_packets = []

        # TLS 1.3 session with secure ciphers
        ch3_data = make_client_hello(0x0303, [0x1301, 0x1302, 0x1303])  # TLS 1.2 (1.3 uses 1.2 in record)
        secure_packets.append(Ether()/IP(src="192.168.1.200", dst="1.1.1.1")/TCP(sport=54321, dport=443, flags="PA")/Raw(load=ch3_data))

        sh3_data = make_server_hello(0x0303, 0x1301)  # TLS_AES_128_GCM_SHA256
        secure_packets.append(Ether()/IP(src="1.1.1.1", dst="192.168.1.200")/TCP(sport=443, dport=54321, flags="PA")/Raw(load=sh3_data))

        wrpcap("test_captures/secure_tls.pcap", secure_packets)
        print("  ✓ Created secure_tls.pcap with TLS 1.3 ciphers")
        print()
        
    except Exception as e:
        print(f"  Error creating secure pcap: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Mixed - include complete sessions (ClientHello + ServerHello for each)
    print("Generating mixed_tls.pcap...")
    try:
        # Include one vulnerable session (RC4) and one secure session, both complete
        # vulnerable_packets[2] = ClientHello RC4, vulnerable_packets[3] = ServerHello RC4
        # secure_packets[0] = ClientHello secure, secure_packets[1] = ServerHello secure
        mixed_packets = [vulnerable_packets[2], vulnerable_packets[3], secure_packets[0], secure_packets[1]]
        wrpcap("test_captures/mixed_tls.pcap", mixed_packets)
        print("  ✓ Created mixed_tls.pcap with complete sessions")
        print()
    except Exception as e:
        print(f"  Error creating mixed pcap: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Client offers export but server doesn't select it
    print("Generating offered_not_selected.pcap...")
    try:
        offered_packets = []
        # Client offers export cipher (0x0003) but server selects secure cipher
        ch_data = make_client_hello(0x0303, [0x0003, 0x1301, 0x1302])  # Offers export + secure
        offered_packets.append(Ether()/IP(src="192.168.1.150", dst="1.1.1.1")/TCP(sport=55555, dport=443, flags="PA")/Raw(load=ch_data))

        sh_data = make_server_hello(0x0303, 0x1301)  # Selects secure cipher
        offered_packets.append(Ether()/IP(src="1.1.1.1", dst="192.168.1.150")/TCP(sport=443, dport=55555, flags="PA")/Raw(load=sh_data))

        wrpcap("test_captures/offered_not_selected.pcap", offered_packets)
        print("  ✓ Created offered_not_selected.pcap (export offered but not selected)")
        print()
    except Exception as e:
        print(f"  Error creating offered_not_selected pcap: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Multiple different export ciphers
    print("Generating multiple_export.pcap...")
    try:
        multi_export_packets = []
        # Session with different export cipher (0x0006)
        ch_data = make_client_hello(0x0301, [0x0006, 0x000B])
        multi_export_packets.append(Ether()/IP(src="10.0.0.100", dst="8.8.8.8")/TCP(sport=60000, dport=443, flags="PA")/Raw(load=ch_data))

        sh_data = make_server_hello(0x0301, 0x0006)  # TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5
        multi_export_packets.append(Ether()/IP(src="8.8.8.8", dst="10.0.0.100")/TCP(sport=443, dport=60000, flags="PA")/Raw(load=sh_data))

        wrpcap("test_captures/multiple_export.pcap", multi_export_packets)
        print("  ✓ Created multiple_export.pcap (different export cipher)")
        print()
    except Exception as e:
        print(f"  Error creating multiple_export pcap: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. RC4 without export
    print("Generating rc4_only.pcap...")
    try:
        rc4_packets = []
        # Client offers RC4 cipher (0x0004 - RSA_WITH_RC4_128_MD5) that's not export
        ch_data = make_client_hello(0x0301, [0x0004, 0x002f])
        rc4_packets.append(Ether()/IP(src="192.168.1.110", dst="198.51.100.1")/TCP(sport=33333, dport=443, flags="PA")/Raw(load=ch_data))

        sh_data = make_server_hello(0x0301, 0x0004)  # RC4 but not export
        rc4_packets.append(Ether()/IP(src="198.51.100.1", dst="192.168.1.110")/TCP(sport=443, dport=33333, flags="PA")/Raw(load=sh_data))

        wrpcap("test_captures/rc4_only.pcap", rc4_packets)
        print("  ✓ Created rc4_only.pcap (RC4 without export)")
        print()
    except Exception as e:
        print(f"  Error creating rc4_only pcap: {e}")
        import traceback
        traceback.print_exc()
        return

    # 7. Weak DH parameters
    print("Generating weak_dh.pcap...")
    try:
        def make_client_hello_with_dh(version, ciphers, supported_groups):
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

        weak_dh_packets = []
        # Use DHE cipher and advertise very weak DH group
        # Supported groups: 256 (ffdhe2048), but we'll simulate weak 512-bit DH
        ch_data = make_client_hello_with_dh(0x0303, [0x0033, 0x0039], [256, 257])
        weak_dh_packets.append(Ether()/IP(src="192.168.1.120", dst="203.0.113.1")/TCP(sport=44444, dport=443, flags="PA")/Raw(load=ch_data))

        sh_data = make_server_hello(0x0303, 0x0033)  # TLS_DHE_RSA_WITH_AES_128_CBC_SHA
        weak_dh_packets.append(Ether()/IP(src="203.0.113.1", dst="192.168.1.120")/TCP(sport=443, dport=44444, flags="PA")/Raw(load=sh_data))

        wrpcap("test_captures/weak_dh.pcap", weak_dh_packets)
        print("  ✓ Created weak_dh.pcap (with DH parameters)")
        print()
    except Exception as e:
        print(f"  Error creating weak_dh pcap: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify packets by reading back
    print("\n  Verifying pcap by reading back...", file=sys.stderr)
    verify_packets = rdpcap("test_captures/vulnerable_tls.pcap")
    print(f"  Read back {len(verify_packets)} packets", file=sys.stderr)
    for i, p in enumerate(verify_packets):
        has_raw = p.haslayer(Raw)
        print(f"  Packet {i}: Has Raw = {has_raw}", file=sys.stderr)
        if has_raw:
            raw_data = p[Raw].load
            if len(raw_data) >= 6:
                hs_type = raw_data[5]
                hs_name = {1: 'ClientHello', 2: 'ServerHello'}.get(hs_type, 'Unknown')
                print(f"    Handshake: {hs_type} ({hs_name})", file=sys.stderr)
    
    print("Test pcap files generated successfully!")

if __name__ == "__main__":
    create_test_captures()
EOFPYTHON
echo

# Run analyzer on vulnerable pcap
echo "Analyzing vulnerable_tls.pcap..."
python3 tls_security_analyzer.py test_captures/vulnerable_tls.pcap -o report.json -v
echo

# Run analyzer on secure pcap
echo "Analyzing secure_tls.pcap..."
python3 tls_security_analyzer.py test_captures/secure_tls.pcap -o secure_report.json -v
echo

# Run analyzer on mixed pcap
echo "Analyzing mixed_tls.pcap..."
python3 tls_security_analyzer.py test_captures/mixed_tls.pcap -o mixed_report.json -v
echo

echo "=== Analysis Complete ==="
echo "Reports generated:"
echo "  - report.json (vulnerable sessions)"
echo "  - secure_report.json (secure sessions)"
echo "  - mixed_report.json (mixed sessions)"
echo

# Debug: Show report.json structure
echo "=== DEBUG: Report structure ==="
python3 << 'EOF'
import json
try:
    report = json.load(open('report.json'))
    print(f"Total sessions: {len(report['sessions'])}")
    for i, s in enumerate(report['sessions']):
        print(f"\nSession {i}: {s['session_id']}")
        print(f"  Connection: {s['connection']['src_ip']}:{s['connection']['src_port']} -> {s['connection']['dst_ip']}:{s['connection']['dst_port']}")
        print(f"  Client ciphers: {len(s['cipher_suites']['client_offered'])}")
        for c in s['cipher_suites']['client_offered']:
            print(f"    - {c['id']}: {c['name']}")
        selected = s['cipher_suites']['server_selected']
        if selected:
            print(f"  Server cipher: {selected['id']}: {selected['name']}")
        else:
            print(f"  Server cipher: None")
        print(f"  Vulnerabilities: {s['vulnerabilities']}")
except Exception as e:
    print(f"Error reading report: {e}")
    import traceback
    traceback.print_exc()
EOF
echo
