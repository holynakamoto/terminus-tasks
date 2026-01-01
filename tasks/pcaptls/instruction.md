# TLS Security Analyzer

## Task Description

Implement a script that analyzes TLS network traffic captures (pcap files) and generates comprehensive security vulnerability reports.

## Requirements

### 1. Traffic Ingestion
- Accept pcap files as input
- Support both tshark and scapy for parsing (fallback if one unavailable)
- Extract TLS handshake messages (Client Hello, Server Hello)

### 2. Data Extraction
- Extract all cipher suites offered by clients
- Extract cipher suite selected by server
- Extract Diffie-Hellman groups/parameters
- Extract DH prime sizes when available
- Record session timestamps and connection metadata (IPs, ports)

### 3. Vulnerability Detection
- Flag sessions using export-grade cipher suites
- Flag sessions using RC4 cipher suites
- Flag DH parameters with primes under 1024 bits
- Distinguish between offered vs. selected vulnerable ciphers

### 4. Report Generation
- Output structured JSON report
- Include per-session analysis with:
  * Session identifier and timestamp
  * Source/destination IP and port
  * Client offered cipher suites (with names)
  * Server selected cipher suite (with name)
  * DH groups and prime sizes
  * List of vulnerabilities detected
  * Vulnerability status flag
- Include summary statistics:
  * Total sessions analyzed
  * Count of vulnerable sessions
  * Breakdown by vulnerability type

### 5. Implementation Quality
- Handle multiple TLS sessions in single pcap
- Proper error handling for malformed packets
- Command-line interface with options for output file and analysis method
- Clear documentation and usage examples

## Expected Output Format

The script should produce JSON output in the following format:

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
      "timestamp_unix": 1703952330.0,
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

## Vulnerability Definitions

### Export-Grade Ciphers
Export-grade cryptography was intentionally weakened (40-56 bit keys) to comply with 1990s US export restrictions. These ciphers are trivially breakable today.

**Cipher IDs**: 0x0003, 0x0006, 0x0008, 0x000B, 0x000E, 0x0011, 0x0014, 0x0017, 0x0019, 0x0026, 0x0027, 0x0028, 0x0029, 0x002A, 0x002B, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066

**Vulnerability Types**:
- `EXPORT_GRADE_CIPHER`: Server selected an export cipher
- `EXPORT_CIPHER_OFFERED`: Client offered export ciphers (even if not selected)

### RC4 Ciphers
RC4 is a stream cipher with well-documented biases that enable practical attacks. Deprecated by RFC 7465 in 2015.

**Cipher IDs**: 0x0003, 0x0004, 0x0005, 0x0017, 0x0018, 0x0020, 0x0024, 0x0028, 0xC002, 0xC007, 0xC00C, 0xC011, 0xC016, 0xC01B, 0xC020

**Vulnerability Types**:
- `RC4_CIPHER`: Server selected an RC4 cipher
- `RC4_CIPHER_OFFERED`: Client offered RC4 ciphers (even if not selected)

### Weak Diffie-Hellman
DH groups with primes under 1024 bits are vulnerable to pre-computation attacks and should not be used.

**Vulnerability Type**:
- `WEAK_DH_PARAMETERS`: DH prime size < 1024 bits

## Hints

- Use `tshark -Y "tls.handshake.type"` to filter TLS handshake packets
- TLS handshake types: 1=ClientHello, 2=ServerHello
- Export cipher suites typically have "EXP" in their name and small key sizes
- RC4 cipher suites have identifiable cipher IDs (0x0004, 0x0005, etc.)
- DH prime size under 1024 bits is considered cryptographically weak
- Scapy TLS layers: TLSClientHello, TLSServerHello
- Consider offering both tshark and scapy as analysis backends for flexibility

## Usage Example

```bash
# Basic usage (outputs to stdout)
python3 tls_security_analyzer.py capture.pcap

# Save to file
python3 tls_security_analyzer.py capture.pcap --output report.json

# Specify method (tshark or scapy backend)
python3 tls_security_analyzer.py capture.pcap --method tshark
python3 tls_security_analyzer.py capture.pcap --method scapy

# Verbose output
python3 tls_security_analyzer.py capture.pcap --verbose
```

## Testing

Test pcap files are generated in `test_captures/` with numbered filenames (`capture_1.pcap`, `capture_2.pcap`, etc.). These files contain various TLS session configurations to test different aspects of your analyzer:
- Detecting when vulnerabilities are offered vs. selected
- Handling multiple types of vulnerable ciphers (export-grade, RC4)
- Proper backend selection (tshark vs. scapy)
- DH parameter extraction and analysis
- Distinguishing secure vs. vulnerable sessions

## References

- [RFC 7465 - Prohibiting RC4 Cipher Suites](https://tools.ietf.org/html/rfc7465)
- [RFC 7919 - Negotiated Finite Field Diffie-Hellman](https://tools.ietf.org/html/rfc7919)
- [FREAK Attack (CVE-2015-0204)](https://freakattack.com/)
- [Logjam Attack](https://weakdh.org/)


<!-- Updated 1767285257 -->
