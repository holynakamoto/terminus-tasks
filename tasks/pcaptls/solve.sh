#!/bin/bash
# Generate test PCAP files for TLS Security Analyzer testing

set -e

echo "Generating test PCAP files..."

# Create test captures directory
mkdir -p test_captures

# Generate test captures using Python/Scapy
python3 << 'EOF'
from scapy.all import *
from scapy.layers.inet import IP, TCP
from scapy.layers.tls.all import *
from scapy.layers.tls.handshake import TLSClientHello, TLSServerHello, TLS13ServerHello
from scapy.layers.tls.extensions import *
from scapy.layers.tls.record import TLS
import struct

def create_client_hello(src_ip, dst_ip, src_port, dst_port, ciphers, timestamp=None):
    """Create a TLS ClientHello packet"""
    ip = IP(src=src_ip, dst=dst_ip)
    tcp_syn = TCP(sport=src_port, dport=dst_port, flags='S', seq=1000)
    tcp_ack = TCP(sport=src_port, dport=dst_port, flags='A', seq=1001, ack=1001)

    # Create TLS ClientHello
    cipher_suites = ciphers

    # Supported groups extension (for DH)
    supported_groups = TLS_Ext_SupportedGroups(groups=[23, 24, 25])  # secp256r1, secp384r1, secp521r1

    client_hello = TLSClientHello(
        ciphers=cipher_suites,
        ext=[supported_groups]
    )

    tls_record = TLS(msg=[client_hello])

    return [ip/tcp_syn, ip/TCP(sport=src_port, dport=dst_port, flags='SA', seq=1000, ack=1001),
            ip/tcp_ack, ip/tcp_ack/tls_record]

def create_server_hello(src_ip, dst_ip, src_port, dst_port, cipher):
    """Create a TLS ServerHello packet"""
    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(sport=src_port, dport=dst_port, flags='A', seq=1001, ack=2001)

    server_hello = TLSServerHello(cipher=cipher)
    tls_record = TLS(msg=[server_hello])

    return ip/tcp/tls_record

# Capture 1: Export-grade and RC4 ciphers
print("Creating capture_1.pcap (export and RC4 vulnerabilities)...")
packets = []

# Session 1: Export cipher (TLS_RSA_EXPORT_WITH_RC4_40_MD5 = 0x0003)
packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54321, 443,
    [0x0003, 0x0004, 0x0005, 0x002f, 0xc014]  # Include export cipher
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54321,
    0x0003  # Server selects export cipher
))

# Session 2: RC4 cipher (TLS_RSA_WITH_RC4_128_MD5 = 0x0004)
packets.extend(create_client_hello(
    "192.168.1.101", "93.184.216.34", 54322, 443,
    [0x0004, 0x0005, 0x002f, 0xc014]  # Include RC4 cipher
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.101", 443, 54322,
    0x0004  # Server selects RC4 cipher
))

wrpcap("test_captures/capture_1.pcap", packets)

# Capture 2: Secure traffic only
print("Creating capture_2.pcap (secure traffic)...")
packets = []

# Session 1: Modern secure cipher (TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 = 0xc02f)
packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54323, 443,
    [0xc02f, 0xc030, 0x002f]  # Only secure ciphers
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54323,
    0xc02f  # Server selects secure cipher
))

wrpcap("test_captures/capture_2.pcap", packets)

# Capture 3: Mixed traffic with complete metadata
print("Creating capture_3.pcap (mixed traffic)...")
packets = []

# Session 1: Vulnerable
packets.extend(create_client_hello(
    "10.0.0.50", "1.2.3.4", 49152, 443,
    [0x0003, 0x002f, 0xc02f]
))
packets.append(create_server_hello(
    "1.2.3.4", "10.0.0.50", 443, 49152,
    0x0003
))

# Session 2: Secure
packets.extend(create_client_hello(
    "10.0.0.51", "1.2.3.4", 49153, 443,
    [0x002f, 0xc02f]
))
packets.append(create_server_hello(
    "1.2.3.4", "10.0.0.51", 443, 49153,
    0xc02f
))

wrpcap("test_captures/capture_3.pcap", packets)

# Capture 4: Export offered but not selected
print("Creating capture_4.pcap (export offered, not selected)...")
packets = []

packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54324, 443,
    [0x0003, 0xc02f]  # Client offers export
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54324,
    0xc02f  # Server selects secure cipher
))

wrpcap("test_captures/capture_4.pcap", packets)

# Capture 5: Different export cipher (TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5 = 0x0006)
print("Creating capture_5.pcap (different export cipher 0x0006)...")
packets = []

packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54325, 443,
    [0x0006, 0x002f]
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54325,
    0x0006  # TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5
))

wrpcap("test_captures/capture_5.pcap", packets)

# Capture 6: RC4 only (no export)
print("Creating capture_6.pcap (RC4 only)...")
packets = []

packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54326, 443,
    [0x0004, 0xc02f]  # RC4 cipher
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54326,
    0x0004  # Server selects RC4
))

wrpcap("test_captures/capture_6.pcap", packets)

# Capture 7: Weak DH parameters
print("Creating capture_7.pcap (weak DH parameters)...")
packets = []

# ClientHello with DHE cipher
packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54327, 443,
    [0x0033, 0xc02f]  # TLS_DHE_RSA_WITH_AES_128_SHA
))

# ServerHello with DHE cipher selected
server_hello_pkt = create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54327,
    0x0033
)
packets.append(server_hello_pkt)

# Add Server Key Exchange with weak 512-bit DH prime
# This is a simplified representation - in real TLS, this would be more complex
ip = IP(src="93.184.216.34", dst="192.168.1.100")
tcp = TCP(sport=443, dport=54327, flags='A', seq=2001, ack=3001)

# Create a minimal Server Key Exchange message with DH params
# In practice, Scapy might not have full support for this, so we'll add raw bytes
# The important part is the prime length (512 bits = 64 bytes)
dh_p_length = 64  # 512 bits / 8 = 64 bytes (weak!)
dh_p = b'\xff' * dh_p_length
dh_g = b'\x02'
dh_Ys_length = 64
dh_Ys = b'\xaa' * dh_Ys_length

# Construct server key exchange payload
ske_data = struct.pack('!H', dh_p_length) + dh_p
ske_data += struct.pack('!H', len(dh_g)) + dh_g
ske_data += struct.pack('!H', dh_Ys_length) + dh_Ys

# Wrap in TLS record (handshake type 12 = ServerKeyExchange)
handshake_msg = struct.pack('!B', 12) + struct.pack('!I', len(ske_data))[1:] + ske_data
tls_record = struct.pack('!BHH', 0x16, 0x0303, len(handshake_msg)) + handshake_msg

packets.append(ip/tcp/Raw(load=tls_record))

wrpcap("test_captures/capture_7.pcap", packets)

# Capture 8: Malformed packets
print("Creating capture_8.pcap (with malformed packets)...")
packets = []

# Valid session first
packets.extend(create_client_hello(
    "192.168.1.100", "93.184.216.34", 54328, 443,
    [0xc02f, 0x002f]
))
packets.append(create_server_hello(
    "93.184.216.34", "192.168.1.100", 443, 54328,
    0xc02f
))

# Add malformed TLS packet
ip = IP(src="192.168.1.100", dst="93.184.216.34")
tcp = TCP(sport=54329, dport=443, flags='A')
malformed_tls = Raw(load=b'\x16\x03\x03\xff\xff' + b'\x00' * 100)  # Invalid length
packets.append(ip/tcp/malformed_tls)

# Add truncated packet
truncated_tls = Raw(load=b'\x16\x03\x03')  # Incomplete header
packets.append(ip/tcp/truncated_tls)

wrpcap("test_captures/capture_8.pcap", packets)

print("✓ All test PCAP files generated successfully")
EOF

echo "✓ Test PCAP generation complete"
