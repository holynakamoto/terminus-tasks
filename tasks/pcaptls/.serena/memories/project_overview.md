# Project Overview: TLS Security Analyzer

## Purpose
A comprehensive tool for analyzing TLS traffic captures (PCAP files) and identifying cryptographic vulnerabilities including:
- Export-grade ciphers (weak 40/56-bit encryption from 1990s)
- RC4 ciphers (deprecated stream cipher with known biases)
- Weak Diffie-Hellman parameters (DH prime sizes under 1024 bits)

The analyzer produces detailed JSON reports with session-level granularity.

## Tech Stack
- **Language**: Python 3.13.11
- **Primary Dependencies**: 
  - `scapy` (optional) - for TLS packet parsing
  - `tshark` (optional) - alternative packet parsing backend
  - Standard library: `argparse`, `json`, `subprocess`, `struct`, `datetime`, `typing`, `pathlib`
- **System**: Darwin (macOS)
- **Category**: Security, networking, cryptography

## Project Structure
```
.
├── tls_security_analyzer.py  # Main analyzer script
├── tests/                     # Test suite
│   ├── test_outputs.py       # Python test assertions
│   └── test.sh               # Bash test runner
├── solution/                  # Reference solution
│   └── solve.sh              # Solution script that generates test data
├── environment/              # Docker environment config
├── README.md                 # User-facing documentation
├── instruction.md            # Task requirements and specifications
├── task.toml                 # Task metadata and configuration
└── TDG.md                    # Additional documentation

```

## Key Features
- **Dual Analysis Backends**: Supports both tshark and Scapy for maximum compatibility with automatic fallback
- **Comprehensive Detection**: Identifies both selected and offered vulnerable ciphers
- **Detailed Reporting**: JSON output with session metadata (IPs, ports, timestamps)
- **Cipher Suite Resolution**: Converts cipher suite IDs to human-readable names
- **Vulnerability Tracking**: Distinguishes between offered vs. selected vulnerabilities

## Architecture
The codebase uses a modular, class-based design:
- `TLSSession`: Represents a TLS session with security parameters
- `TSharkAnalyzer`: Backend for tshark-based analysis
- `ScapyAnalyzer`: Backend for Scapy-based analysis
- `ManualTLSParser`: Fallback manual parser for raw TLS bytes
- Vulnerability detection through comparison with known cipher sets
- Report generation with comprehensive metadata
