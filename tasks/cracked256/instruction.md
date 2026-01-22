# Password Recovery Tool

You are tasked with building a password recovery tool for a security audit. The system has captured PBKDF2-HMAC-SHA256 password hashes from a legacy application. Your tool must parse these hashes, apply password transformation rules, and recover as many passwords as possible.

## Input Files

The input file `/app/hashes.txt` contains hashes in this format:
```
username:pbkdf2_sha256$iterations$salt_base64$hash_base64
```

Example:
```
alice:pbkdf2_sha256$10000$c2FsdDEyMzQ=$qYvT8z9K3xJ2nL5wR7fH4pM9vN8bC3dE1fG2hI3jK4=
```

**Note**: Some entries may be malformed (wrong format, missing components, invalid base64). Your parser should handle these gracefully without crashing.

The dictionary file `/app/dictionary.txt` contains base password candidates (one per line).

## Requirements

1. **Parse hashes** - Read `/app/hashes.txt` and extract valid PBKDF2 entries. Skip malformed entries.

2. **Apply transformations** - Generate password candidates by modifying dictionary words:
   - Capitalization: `password` → `Password`, `PASSWORD`
   - Leet speak: `password` → `p@ssw0rd`, `admin` → `@dm1n`
   - Numeric suffixes: `password` → `password123`, `admin2024`
   - Symbol suffixes: `hello` → `hello!`, `welcome@`
   - **Combined transformations** (most common): `password` → `P@ssw0rd123!`, `admin` → `@dm1n2024`, `master` → `M@st3r!`
     - Example: Start with `password`, capitalize → `Password`, apply leet speak → `P@ssw0rd`, add number → `P@ssw0rd123`, add symbol → `P@ssw0rd123!`

3. **Optimize processing**:
   - Group hashes by iteration count for batch processing
   - Process low iteration counts first (1000, 5000) before high counts (10000)
   - This significantly reduces computation time

4. **Output format** - Write to `/app/cracked.csv`:
   ```
   CRACKED_BY_TERMINUS_AGENT_2026
   username,password
   alice,Password123
   bob,admin2024
   ```
   - First line: `CRACKED_BY_TERMINUS_AGENT_2026`
   - Second line: CSV header `username,password`
   - Sort by username alphabetically

## Implementation Tips

- Use Python's `hashlib.pbkdf2_hmac('sha256', password, salt, iterations)` to compute hashes
- Parse the hash format carefully: `pbkdf2_sha256$iterations$salt$hash`
- Decode base64 salt and hash using `base64.b64decode()`
- Empty salts are possible (handle `salt_b64 = ''`)
- Target at least 30% crack rate (3+ out of 10 valid hashes)
- At least 40% of cracked passwords must demonstrate combined transformations (e.g., `P@ssw0rd123!`)

## Constraints

- Use absolute paths: `/app/hashes.txt`, `/app/dictionary.txt`, `/app/cracked.csv`
- Output file must be a regular file (not a symlink)
- Do not modify input files
- Complete within timeout (15 minutes)

