# Enterprise Password Recovery System

You are tasked with building a production-grade password recovery tool for a security audit. The system has captured authentication hashes from a legacy application. Your tool must parse these hashes, apply industry-standard password transformation techniques, and recover as many passwords as possible within the time limit.

## Input Files

The input file `/app/hashes.txt` contains authentication hashes in a colon-delimited format:

```
username:hash_algorithm$parameters$encoded_data
```

The hashes primarily use PBKDF2-HMAC-SHA256, with parameters including iteration counts, salt values (Base64-encoded), and the final hash output (Base64-encoded).

**Note**: Some entries may have formatting inconsistencies from the data export process. Your parser should be robust enough to handle real-world data quality issues while correctly processing valid entries.

Example valid entry:
```
alice:pbkdf2_sha256$10000$c2FsdDEyMzQ=$qYvT8z9K3xJ2nL5wR7fH4pM9vN8bC3dE1fG2hI3jK4=
```

A dictionary file `/app/dictionary.txt` contains base password candidates (one per line).

## Requirements

Your tool must:

1. **Parse and validate** the input file, handling any malformed or inconsistent entries gracefully without crashing

2. **Apply password transformations** to dictionary words using patterns commonly observed in password research. Your transformations should be comprehensive enough to crack challenging passwords that combine multiple modification patterns. A production-grade solution is expected to successfully recover a high proportion (at least 40%) of passwords requiring these complex multi-rule transformations (e.g., combinations of capitalization, leet speak, and numeric suffixes).

3. **Efficiently process the hashes** using appropriate techniques. Performance matters - a naive brute-force approach may timeout. The dataset contains varying iteration counts that require optimization strategies.

4. **Output results** to `/app/cracked.csv` in CSV format with columns: `username,password`
   - Include only successfully cracked passwords
   - Sort output alphabetically by username
   - Include the header `CRACKED_BY_TERMINUS_AGENT_2026` as the first line (before the CSV header)

## Output Format

The output file `/app/cracked.csv` must contain:
- Line 1: `CRACKED_BY_TERMINUS_AGENT_2026`
- Line 2: CSV header `username,password`
- Subsequent lines: Recovered credentials, one per line, sorted alphabetically by username

## Implementation Constraints

- You may use any tools or libraries available in the environment
- Solution must complete within the timeout period
- Handle edge cases gracefully: some entries may have unusual parameters (empty salts, extreme iteration counts, malformed formatting)
- Use absolute paths: `/app/hashes.txt`, `/app/dictionary.txt`, `/app/cracked.csv`
- **Maintain data integrity**: The system validates the integrity of the captured data. Do not attempt to modify `/app/hashes.txt` or `/app/dictionary.txt` as this will invalidate the audit results.

## Evaluation

Your solution will be evaluated on:
- Robustness of hash format parsing (handles malformed entries without crashing)
- Effectiveness of password transformation techniques (recovers passwords with complex transformations)
- Number of successfully recovered passwords (minimum 30% of valid hashes)
- Correct output format and alphabetical sorting
- Ability to complete within timeout constraints
