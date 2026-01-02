# Code Style and Conventions

## Python Style Guide

### Type Hints
- **Always use type hints** from the `typing` module for function parameters and return values
- Common types used:
  - `List[int]`, `List[TLSSession]`, `Dict[str, Any]`
  - `Optional[int]`, `Optional[Path]` for nullable values
  - `Path` from `pathlib` for file paths

Example:
```python
def analyze_pcap(pcap_file: Path) -> List[TLSSession]:
    """Extract TLS sessions from pcap."""
```

### Docstrings
- **Use triple-quoted docstrings** for all functions and classes
- Format: Google-style with clear description, Args, and Returns sections
- Example:
```python
def generate_report(sessions: List[TLSSession], output_file: Optional[Path] = None) -> Dict[str, Any]:
    """Generate JSON report from analyzed sessions.

    Args:
        sessions: List of TLS sessions to include in report
        output_file: Optional path to write JSON output

    Returns:
        Dictionary containing the complete analysis report
    """
```

### Naming Conventions
- **Constants**: UPPERCASE_WITH_UNDERSCORES
  - Examples: `EXPORT_CIPHERS`, `RC4_CIPHERS`, `NAMED_DH_GROUPS`
- **Classes**: PascalCase
  - Examples: `TLSSession`, `TSharkAnalyzer`, `ScapyAnalyzer`
- **Functions/Methods**: snake_case
  - Examples: `analyze_vulnerabilities()`, `generate_report()`, `parse_client_hello()`
- **Variables**: snake_case
  - Examples: `session_id`, `client_ciphers`, `dh_prime_size`

### Code Organization
- **Class-based design** for analyzers and data models
- **Static methods** for utility functions that don't need instance state
- **Constants** defined at module level before classes
- **Main entry point** using `if __name__ == "__main__":`

### Error Handling
- Use try/except blocks for operations that may fail
- Print errors to `sys.stderr`
- Return meaningful error codes (sys.exit(1) for errors, sys.exit(0) for success)
- Handle missing dependencies gracefully (e.g., SCAPY_AVAILABLE flag)

Example:
```python
try:
    from scapy.all import rdpcap
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
```

### Command-Line Interface
- Use `argparse` for CLI argument parsing
- Provide clear help text and examples
- Support standard flags: `-o/--output`, `-m/--method`, `-v/--verbose`

### Data Structures
- Use **dictionaries** for mappings (cipher names, DH groups)
- Use **sets** for membership testing (vulnerable cipher IDs)
- Use **lists** for ordered collections
- Use **dataclasses or classes** for structured data (TLSSession)

### Comments
- Code should be self-documenting where possible
- Add comments for complex logic (especially in manual parsing)
- Include references to RFCs and security resources where relevant

### File I/O
- Use `pathlib.Path` for file operations, not string paths
- Use context managers (`with` statements) for file operations
- Handle file existence checks before operations
