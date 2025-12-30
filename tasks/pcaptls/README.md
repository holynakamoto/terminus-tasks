# TLS Security Analyzer

A comprehensive tool for analyzing TLS traffic captures and identifying cryptographic vulnerabilities.

## Overview

This script analyzes packet capture (pcap) files containing TLS handshake traffic to identify security vulnerabilities including:

- **Export-grade ciphers**: Weak 40/56-bit encryption from the 1990s
- **RC4 ciphers**: Stream cipher with known biases (deprecated in RFC 7465)
- **Weak Diffie-Hellman**: DH prime sizes under 1024 bits

## Features

- **Dual Analysis Backends**: Supports both tshark and Scapy for maximum compatibility
- **Comprehensive Detection**: Identifies both selected and offered vulnerable ciphers
- **Detailed Reporting**: JSON output with session-level granularity
- **Connection Metadata**: Tracks source/destination IPs, ports, and timestamps
- **Cipher Suite Naming**: Resolves cipher suite IDs to human-readable names

## Requirements

```bash
# Option 1: tshark (recommended)
apt-get install tshark

# Option 2: Scapy
pip install scapy

# Both can be installed for maximum compatibility
```

## Usage

### Basic Usage

```bash
# Analyze pcap file
python3 tls_security_analyzer.py capture.pcap

# Save results to JSON file
python3 tls_security_analyzer.py capture.pcap --output report.json

# Specify analysis method
python3 tls_security_analyzer.py capture.pcap --method tshark
python3 tls_security_analyzer.py capture.pcap --method scapy

# Verbose output
python3 tls_security_analyzer.py capture.pcap -v
```

### Example Output

```json
{
  "analysis_metadata": {
    "timestamp": "2024-12-30T15:30:00",
    "total_sessions": 5,
    "vulnerable_sessions": 3
  },
  "vulnerability_summary": {
    "export_grade_ciphers": 1,
    "rc4_ciphers": 2,
    "weak_dh_parameters": 1,
    "export_cipher_offered": 0,
    "rc4_cipher_offered": 1
  },
  "sessions": [
    {
      "session_id": "192.168.1.100:54321-93.184.216.34:443",
      "timestamp": "2024-12-30T15:25:30",
      "connection": {
        "src_ip": "192.168.1.100",
        "src_port": 54321,
        "dst_ip": "93.184.216.34",
        "dst_port": 443
      },
      "cipher_suites": {
        "client_offered": [
          {"id": "0x0003", "name": "TLS_RSA_EXPORT_WITH_RC4_40_MD5"},
          {"id": "0x002F", "name": "TLS_RSA_WITH_AES_128_CBC_SHA"}
        ],
        "server_selected": {
          "id": "0x0003",
          "name": "TLS_RSA_EXPORT_WITH_RC4_40_MD5"
        }
      },
      "diffie_hellman": {
        "supported_groups": [23, 24, 25],
        "named_groups": ["unknown_23", "unknown_24", "unknown_25"],
        "prime_size_bits": null
      },
      "vulnerabilities": ["EXPORT_GRADE_CIPHER"],
      "is_vulnerable": true
    }
  ]
}
```

## Vulnerability Details

### Export-Grade Ciphers

Export-grade cryptography was intentionally weakened (40-56 bit keys) to comply with 1990s US export restrictions. These ciphers are trivially breakable today.

**Cipher IDs**: 0x0003, 0x0006, 0x0008, 0x000B, 0x000E, and others

**Vulnerability Types**:
- `EXPORT_GRADE_CIPHER`: Server selected an export cipher
- `EXPORT_CIPHER_OFFERED`: Client offered export ciphers (even if not selected)

### RC4 Ciphers

RC4 is a stream cipher with well-documented biases that enable practical attacks. Deprecated by RFC 7465 in 2015.

**Cipher IDs**: 0x0004, 0x0005, 0xC007, 0xC011, and others

**Vulnerability Types**:
- `RC4_CIPHER`: Server selected an RC4 cipher
- `RC4_CIPHER_OFFERED`: Client offered RC4 ciphers (even if not selected)

### Weak Diffie-Hellman

DH groups with primes under 1024 bits are vulnerable to pre-computation attacks and should not be used.

**Vulnerability Type**:
- `WEAK_DH_PARAMETERS`: DH prime size < 1024 bits

## Implementation Details

### TShark Backend

Uses `tshark` with field extraction to parse TLS handshake messages:

```bash
tshark -r capture.pcap \
  -Y "tls.handshake.type" \
  -T fields \
  -e frame.time_epoch \
  -e tls.handshake.ciphersuite \
  -e tls.handshake.extensions.supported_group
```

### Scapy Backend

Uses Scapy's TLS layer parsing:

```python
from scapy.layers.tls.all import TLS, TLSClientHello, TLSServerHello
packets = rdpcap('capture.pcap')
```

## Testing

The script includes comprehensive test coverage for various TLS scenarios:

- Vulnerable sessions (export-grade, RC4, weak DH)
- Secure modern TLS 1.3 sessions  
- Mixed environments

Test pcap files can be generated using:

```bash
python3 generate_test_pcaps.py
```

This creates:
- `test_captures/vulnerable_tls.pcap` - Contains vulnerable sessions
- `test_captures/secure_tls.pcap` - Contains only secure sessions
- `test_captures/mixed_tls.pcap` - Mix of vulnerable and secure

## References

- [RFC 7465 - Prohibiting RC4 Cipher Suites](https://tools.ietf.org/html/rfc7465)
- [RFC 7919 - Negotiated Finite Field Diffie-Hellman](https://tools.ietf.org/html/rfc7919)
- [FREAK Attack (CVE-2015-0204)](https://freakattack.com/)
- [Logjam Attack](https://weakdh.org/)

## License

This tool is provided for educational and security research purposes.

