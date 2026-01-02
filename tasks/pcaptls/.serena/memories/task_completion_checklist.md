# Task Completion Checklist

When you finish implementing or modifying code for this project, follow this checklist to ensure quality and correctness.

## 1. Run the Test Suite

**Primary requirement:**
```bash
bash tests/test.sh
```

The test suite validates:
- ✅ Valid JSON output structure
- ✅ Export-grade cipher detection
- ✅ RC4 cipher detection  
- ✅ Weak DH parameter detection
- ✅ Secure traffic validation (no false positives)
- ✅ Session metadata completeness
- ✅ Cipher suite naming (ID and human-readable)
- ✅ Offered vs. selected cipher distinction
- ✅ Backend selection (tshark/scapy) and fallback
- ✅ Multiple export cipher types
- ✅ RC4-only detection
- ✅ Complete JSON field validation
- ✅ Malformed packet handling
- ✅ Anti-hardcoding verification

**All tests must pass** before considering the task complete.

## 2. Verify JSON Output Format

Ensure the generated reports match the expected structure:

```bash
python3 tls_security_analyzer.py test_captures/capture_1.pcap -o test_report.json
python3 -m json.tool test_report.json > /dev/null && echo "✓ Valid JSON"
```

Check that the report contains:
- `analysis_metadata` with `timestamp`, `total_sessions`, `vulnerable_sessions`
- `vulnerability_summary` with all vulnerability counters
- `sessions` array with complete session details

## 3. Test Both Backends

Verify that both analysis backends work correctly:

```bash
# Test tshark backend
python3 tls_security_analyzer.py test_captures/capture_1.pcap -m tshark -o tshark_test.json

# Test scapy backend
python3 tls_security_analyzer.py test_captures/capture_1.pcap -m scapy -o scapy_test.json

# Test auto-selection
python3 tls_security_analyzer.py test_captures/capture_1.pcap -o auto_test.json
```

## 4. Code Quality Checks

### Type Hints
- Verify all function signatures have proper type hints
- Check that Optional[] is used for nullable values
- Ensure Path is used for file paths (not str)

### Docstrings
- All functions and classes have descriptive docstrings
- Docstrings include Args and Returns sections
- Complex logic has inline comments

### Error Handling
- Exceptions are caught and reported to stderr
- Missing dependencies are handled gracefully
- Invalid inputs produce helpful error messages
- Malformed packets don't crash the analyzer

## 5. Functionality Verification

### Core Features
- ✅ Export cipher detection (both offered and selected)
- ✅ RC4 cipher detection (both offered and selected)
- ✅ Weak DH parameter detection (< 1024 bits)
- ✅ Secure traffic correctly identified (no false positives)
- ✅ Multiple TLS sessions in single PCAP handled correctly

### Edge Cases
- ✅ Empty PCAP files handled
- ✅ PCAPs with no TLS traffic handled
- ✅ Malformed TLS packets handled gracefully
- ✅ Client offers vulnerable cipher but server doesn't select it

## 6. Performance and Compatibility

**Check that the tool works on Darwin (macOS):**
- Standard Unix commands work correctly
- Path handling works on macOS
- No platform-specific issues

**Dependencies:**
- Tool works when only tshark is available
- Tool works when only scapy is available
- Tool works when both are available
- Appropriate fallback when neither is available

## 7. Documentation

Ensure code changes are reflected in documentation:
- Update README.md if user-facing behavior changed
- Update docstrings for modified functions
- Add comments for complex new logic

## 8. Git Workflow (if applicable)

```bash
git status                          # Check what changed
git diff                            # Review changes
git add <modified_files>            # Stage changes
git commit -m "descriptive message" # Commit with clear message
```

## Success Criteria

Task is complete when:
1. ✅ All tests in `tests/test.sh` pass
2. ✅ JSON output is valid and complete
3. ✅ Both backends (tshark/scapy) work correctly
4. ✅ Code follows project style conventions
5. ✅ All edge cases are handled gracefully
6. ✅ No regressions in existing functionality

## Common Issues to Check

- **Empty sessions list**: Verify PCAP contains TLS traffic and parsers are working
- **Missing cipher names**: Check CIPHER_SUITE_NAMES dictionary is complete
- **Incorrect vulnerability counts**: Ensure both offered and selected vulnerabilities are tracked
- **Backend failures**: Verify dependency availability checks work correctly
- **Session ID mismatches**: Ensure bidirectional session ID generation is consistent
