# Codebase Structure and Architecture

## Main Script: tls_security_analyzer.py

### Top-Level Constants (Module Level)
- `EXPORT_CIPHERS`: Set of export-grade cipher suite IDs
- `RC4_CIPHERS`: Set of RC4 cipher suite IDs  
- `NAMED_DH_GROUPS`: Dictionary mapping group IDs to names (RFC 7919)
- `CIPHER_SUITE_NAMES`: Dictionary mapping cipher IDs to human-readable names
- `SCAPY_AVAILABLE`: Boolean flag for Scapy dependency availability

### Class: TLSSession
**Purpose**: Data model representing a TLS session with security parameters

**Attributes:**
- `session_id`: Unique identifier (format: "ip:port-ip:port")
- `timestamp`: Unix timestamp
- `client_ciphers`: List of cipher suites offered by client
- `server_cipher`: Cipher suite selected by server
- `dh_groups`: List of supported DH groups
- `dh_prime_size`: DH prime size in bits
- `vulnerabilities`: List of vulnerability strings
- `src_ip`, `dst_ip`, `src_port`, `dst_port`: Connection metadata

**Methods:**
- `__init__(session_id, timestamp)`: Initialize session
- `analyze_vulnerabilities()`: Detect and populate vulnerabilities list
- `to_dict()`: Convert to dictionary for JSON serialization

### Class: ManualTLSParser
**Purpose**: Manual TLS parsing from raw bytes (fallback when Scapy fails)

**Static Methods:**
- `parse_tls_record(data)`: Parse TLS record layer
- `parse_handshake(data)`: Parse handshake message
- `parse_client_hello(data)`: Extract client cipher suites
- `parse_server_hello(data)`: Extract server cipher selection
- `parse_server_key_exchange(data)`: Extract DH parameters

### Class: TSharkAnalyzer
**Purpose**: TLS analysis using tshark command-line tool

**Static Methods:**
- `is_available()`: Check if tshark is installed
- `analyze_pcap(pcap_file)`: Parse PCAP using tshark, return TLSSession list

**Implementation Details:**
- Executes tshark with field extraction
- Parses CSV-style output
- Creates bidirectional session IDs for matching ClientHello/ServerHello
- Handles both hex and decimal cipher suite formats

### Class: ScapyAnalyzer
**Purpose**: TLS analysis using Scapy Python library

**Static Methods:**
- `is_available()`: Check if Scapy is imported
- `analyze_pcap(pcap_file)`: Parse PCAP using Scapy, return TLSSession list

**Implementation Details:**
- Uses Scapy's TLS layers (TLSClientHello, TLSServerHello)
- Falls back to ManualTLSParser for packets Scapy can't parse
- Extracts connection info from IP/TCP layers
- Creates bidirectional session IDs

### Function: generate_report
**Purpose**: Generate JSON report from analyzed sessions

**Parameters:**
- `sessions`: List of TLSSession objects
- `output_file`: Optional Path to write JSON
- `verbose`: Boolean for debug output

**Returns:** Dictionary containing complete analysis report

**Report Structure:**
- `analysis_metadata`: Total sessions, vulnerable count, timestamp
- `vulnerability_summary`: Counts by vulnerability type
- `sessions`: List of session dictionaries

### Function: main
**Purpose**: CLI entry point

**Functionality:**
- Parse command-line arguments
- Validate input file exists
- Select analysis backend (tshark/scapy/both with fallback)
- Generate and output report
- Print summary if verbose

## Test Suite: tests/

### test_outputs.py
**Purpose**: Python-based test assertions

**Test Functions:**
- `test_basic_functionality()`: Valid JSON structure
- `test_vulnerable_detection_export()`: Export cipher detection
- `test_vulnerable_detection_rc4()`: RC4 cipher detection
- `test_weak_dh_detection()`: DH parameter validation
- `test_secure_traffic_validation()`: No false positives
- `test_session_details()`: Complete metadata
- `test_cipher_suite_naming()`: ID and name resolution
- `test_anti_hardcoding()`: Verify actual parsing (not hardcoded)

### test.sh
**Purpose**: Comprehensive bash test runner

**Test Coverage:**
1. Basic functionality and JSON validity
2. Export-grade cipher detection
3. RC4 cipher detection
4. Weak DH parameter detection
5. Secure traffic validation
6. Session metadata validation
7. Cipher suite naming
8. Offered vs selected distinction
9. Offered-not-selected behavior
10. Multiple export cipher types
11. RC4-only detection
12. Backend selection and fallback
13. Weak DH vulnerability detection
14. Complete JSON field validation
15. Malformed packet handling

## Solution: solution/solve.sh
**Purpose**: Generate reference implementation and test data

**Functionality:**
- Creates complete tls_security_analyzer.py implementation
- Generates 8 test PCAP files with various TLS configurations
- Runs analyzer on test captures
- Produces example reports
- Includes debug output for verification

## Configuration: task.toml
**Purpose**: Task metadata and environment configuration

**Sections:**
- `[metadata]`: Author, difficulty, category, tags
- `[task]`: Task name and description
- `[task.oracle]`: Reference solution path
- `[task.scoring]`: Test script path
- `[verifier]`: Timeout settings
- `[agent]`: Agent timeout
- `[environment]`: Docker configuration

## Design Patterns

### Dependency Management
- Graceful degradation when dependencies unavailable
- Availability checks before use
- Clear error messages

### Session Tracking
- Bidirectional session IDs (sorted endpoints)
- Session dictionary for matching ClientHello/ServerHello
- Timestamp preservation from packet capture

### Vulnerability Detection
- Constant sets for efficient membership testing
- Separate tracking of offered vs selected vulnerabilities
- Clear vulnerability naming conventions

### Error Handling
- Try/except blocks around external dependencies
- Stderr for error messages
- Exit codes for success/failure
- Graceful handling of malformed packets
