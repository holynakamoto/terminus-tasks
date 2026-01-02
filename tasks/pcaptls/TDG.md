# TDG: pcaptls – TLS PCAP Analyzer

## Goal
Build a tool that analyzes one or more PCAP files containing TLS traffic and produces a comprehensive `report.json` detailing:
- Metadata about the analysis
- Vulnerability summary counters
- Per-session TLS details including cipher suites, vulnerabilities, and connection info

The tool must pass the full verification suite:
- `tests/test.sh` (shell-based oracle)
- `tests/test_outputs.py` (pytest assertions on report structure and content)

## Acceptance Criteria (from existing tests)
1. Generates `report.json` with correct top-level structure:
   - `analysis_metadata` (total_sessions, vulnerable_sessions, timestamp, etc.)
   - `vulnerability_summary` (export_grade_ciphers, rc4_ciphers, weak_dh_parameters)
   - `sessions` list with full per-session details
2. Correctly detects:
   - Export-grade cipher suites → flags `EXPORT_GRADE_CIPHER`
   - RC4 cipher suites → flags `RC4_CIPHER`
   - Weak DH parameters (< threshold) → flags `WEAK_DH_PARAMETERS`
3. Provides both hex ID and human-readable name for cipher suites
4. Includes complete connection metadata (IPs, ports, timestamps)
5. Passes anti-hardcoding checks (uses actual packet data, not static values)
6. Runs from `/app` and produces output in the current directory

## Current Status: Red 🚨
- No analyzer script exists yet
- Running tests → `report.json not found` (first failure in test_outputs.py)

## Next Step
Create the minimal analyzer script skeleton that:
- Runs without crashing
- Produces a valid (but empty/incorrect) `report.json` with the expected top-level keys
- Allows the first test (`test_basic_functionality`) to pass the "file exists" check

Language choice: Python (best ecosystem for PCAP/TLS parsing: scapy, dpkt, or pyshark)

---

## TDG Configuration

### Project Information
- **Language:** Python 3
- **Framework:** CLI tool using scapy for packet analysis
- **Test Framework:** pytest + bash integration tests
- **Dependencies:** scapy 2.5.0, tshark

### Build Command
```bash
# No build required (interpreted Python)
```

### Test Command
```bash
# Run pytest unit tests
pytest tests/test_outputs.py -v

# Run shell integration tests
bash tests/test.sh

# Run all tests
pytest tests/test_outputs.py -v && bash tests/test.sh
```

### Single Test Command
```bash
# Run a specific pytest test by name
pytest tests/test_outputs.py::<test_function_name>

# Or using -k filter
pytest tests/test_outputs.py -k <test_name_pattern>
```

### Coverage Command
```bash
pytest tests/test_outputs.py --cov=. --cov-report=term-missing --cov-report=html
```

### Test File Patterns
- **Test files:** `test_*.py`, `*_test.py`
- **Test directory:** `tests/`
- **Integration tests:** `tests/test.sh`
- **Unit tests:** `tests/test_outputs.py`

### Entry Point
- **Main script:** `tls_security_analyzer.py` (to be created)
- **Working directory:** `/app` (in Docker)
- **Output:** `report.json` in current directory

