# Suggested Commands for TLS Security Analyzer

## Development Commands

### Running the Analyzer

**Basic usage:**
```bash
python3 tls_security_analyzer.py <pcap_file>
```

**Save output to file:**
```bash
python3 tls_security_analyzer.py capture.pcap --output report.json
python3 tls_security_analyzer.py capture.pcap -o report.json
```

**Specify analysis method:**
```bash
# Use tshark backend
python3 tls_security_analyzer.py capture.pcap --method tshark

# Use scapy backend
python3 tls_security_analyzer.py capture.pcap --method scapy

# Auto-select with fallback (default)
python3 tls_security_analyzer.py capture.pcap --method both
```

**Verbose output:**
```bash
python3 tls_security_analyzer.py capture.pcap --verbose
python3 tls_security_analyzer.py capture.pcap -v
```

## Testing Commands

**Run full test suite:**
```bash
bash tests/test.sh
```

**Run specific test:**
```bash
python3 -m pytest tests/test_outputs.py::test_basic_functionality
```

**Run with verbose output:**
```bash
bash tests/test.sh 2>&1 | tee test_output.log
```

## Solution Commands

**Generate reference solution and test data:**
```bash
bash solution/solve.sh
```

This script:
- Creates the full TLS security analyzer implementation
- Generates test PCAP files in `test_captures/`
- Runs the analyzer on test captures
- Produces example reports

## System Utility Commands (Darwin/macOS)

**File operations:**
```bash
ls -la                    # List files with details
find . -name "*.py"       # Find Python files
grep -r "pattern" .       # Search for pattern in files
cat file.txt              # Display file contents
head -n 20 file.txt       # Show first 20 lines
tail -n 20 file.txt       # Show last 20 lines
```

**Git commands:**
```bash
git status                # Show working tree status
git diff                  # Show changes
git log --oneline -10     # Show recent commits
git add <file>            # Stage changes
git commit -m "message"   # Commit changes
```

**Python environment:**
```bash
python3 --version         # Check Python version (currently 3.13.11)
pip3 install scapy        # Install Scapy dependency
which python3             # Show Python location
```

**PCAP analysis tools:**
```bash
tshark -v                 # Check tshark version
tshark -r capture.pcap    # Read PCAP file
tcpdump -r capture.pcap   # Alternative PCAP reader
```

## File Management

**Create test directory:**
```bash
mkdir -p test_captures
```

**Clean up generated files:**
```bash
rm -f *.json              # Remove JSON reports
rm -rf test_captures/     # Remove test PCAP files
```

**Check JSON validity:**
```bash
python3 -m json.tool report.json
python3 -c "import json; json.load(open('report.json'))"
```

## Debugging Commands

**Run with Python debugger:**
```bash
python3 -m pdb tls_security_analyzer.py capture.pcap
```

**Print JSON report structure:**
```bash
python3 << 'EOF'
import json
report = json.load(open('report.json'))
print(f"Sessions: {len(report['sessions'])}")
print(f"Vulnerable: {report['analysis_metadata']['vulnerable_sessions']}")
for s in report['sessions']:
    print(f"  {s['session_id']}: {s['vulnerabilities']}")
EOF
```

**Check dependencies:**
```bash
python3 -c "import scapy; print('Scapy available')"
which tshark && echo "tshark available"
```
