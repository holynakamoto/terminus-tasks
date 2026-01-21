"""
Test suite for PBKDF2 hash cracking task.

Validates that the solution correctly parses PBKDF2 hashes, applies mangling rules,
and outputs cracked passwords in the required CSV format.
"""

from pathlib import Path
import csv
import hashlib
import base64

CANARY_STRING = "CRACKED_BY_TERMINUS_AGENT_2026"
EXPECTED_VALID_HASHES = 10  # Oracle generates exactly 10 valid PBKDF2 entries (minimal viable)
EXPECTED_MALFORMED_HASHES = 3  # Oracle inserts exactly 3 malformed entries


def test_output_file_exists():
    """Verify that the cracked passwords output file was created."""
    output_path = Path("/app/cracked.csv")
    assert output_path.exists(), "Output file /app/cracked.csv does not exist"
    assert output_path.stat().st_size > 0, "Output file is empty"


def test_canary_string_present():
    """Verify canary string is present in output (anti-cheating measure)."""
    output_path = Path("/app/cracked.csv")
    content = output_path.read_text()
    assert CANARY_STRING in content, f"Canary string '{CANARY_STRING}' not found in output"


def test_output_has_csv_header():
    """Verify output contains proper CSV header row."""
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')

    assert len(lines) >= 2, "Output must have at least canary + header row"

    # First line should be canary
    assert lines[0] == CANARY_STRING, "First line must be the canary string"

    # Second line should be CSV header
    assert lines[1] == "username,password", "Second line must be CSV header 'username,password'"


def test_csv_format_valid():
    """Verify output follows valid CSV format."""
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')

    # Skip canary string (first line)
    csv_lines = lines[1:]

    # Parse CSV
    reader = csv.DictReader(csv_lines)
    rows = list(reader)

    assert len(rows) > 0, "CSV must contain at least one cracked password"

    for row in rows:
        assert 'username' in row, "CSV row must have 'username' field"
        assert 'password' in row, "CSV row must have 'password' field"
        assert row['username'], "Username cannot be empty"
        assert row['password'], "Password cannot be empty"


def test_passwords_are_alphabetically_sorted():
    """Verify cracked passwords are sorted alphabetically by username."""
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')

    # Skip canary string
    csv_lines = lines[1:]
    reader = csv.DictReader(csv_lines)
    rows = list(reader)

    usernames = [row['username'] for row in rows]
    sorted_usernames = sorted(usernames)

    assert usernames == sorted_usernames, "Usernames must be sorted alphabetically"


def test_cracked_passwords_are_valid():
    """Verify that cracked passwords actually match the hashes."""
    # Read the hashes file
    hashes_path = Path("/app/hashes.txt")
    assert hashes_path.exists(), "Input hashes file must exist"

    # Parse hashes with robust error handling for malformed entries
    hash_map = {}
    for line in hashes_path.read_text().strip().split('\n'):
        if not line:
            continue

        try:
            username, hash_part = line.split(':', 1)
        except ValueError:
            # Malformed line without colon, skip
            continue

        parts = hash_part.split('$')

        # Only handle PBKDF2-SHA256 format
        if len(parts) < 4 or parts[0] != 'pbkdf2_sha256':
            # Skip non-PBKDF2 entries (bcrypt, argon2, etc.)
            continue

        try:
            # Handle comma-formatted iteration counts (e.g., "100,000")
            iterations_str = parts[1].replace(',', '')
            iterations = int(iterations_str)

            salt_b64 = parts[2]
            hash_b64 = parts[3]

            # Handle empty salt (edge case)
            if salt_b64:
                salt = base64.b64decode(salt_b64)
            else:
                salt = b''

            target_hash = base64.b64decode(hash_b64)

            hash_map[username] = {
                'iterations': iterations,
                'salt': salt,
                'target_hash': target_hash
            }
        except (ValueError, IndexError, base64.binascii.Error):
            # Malformed entry: invalid base64, missing components, etc.
            # Skip gracefully as per instruction requirements
            continue

    # Read cracked passwords
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')
    csv_lines = lines[1:]  # Skip canary
    reader = csv.DictReader(csv_lines)
    cracked = list(reader)

    # Verify each cracked password
    for entry in cracked:
        username = entry['username']
        password = entry['password']

        assert username in hash_map, f"Username {username} not found in hashes file"

        hash_info = hash_map[username]

        # Compute PBKDF2 hash with the claimed password
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            hash_info['salt'],
            hash_info['iterations']
        )

        assert computed_hash == hash_info['target_hash'], \
            f"Password '{password}' does not match hash for user '{username}'"


def test_hashes_file_integrity():
    """
    Verify hashes.txt hasn't been tampered with (anti-cheating measure).

    The oracle generates exactly 60 valid PBKDF2 entries and 5 known malformed entries.
    This test prevents agents from modifying hashes.txt to make cracking easier.
    """
    hashes_path = Path("/app/hashes.txt")
    assert hashes_path.exists(), "Input hashes file must exist"

    lines = hashes_path.read_text().strip().split('\n')

    valid_pbkdf2_count = 0
    malformed_count = 0
    valid_usernames = set()

    for line in lines:
        if not line:
            continue

        try:
            username, hash_part = line.split(':', 1)
        except ValueError:
            malformed_count += 1
            continue

        parts = hash_part.split('$')

        # Check if it's a valid PBKDF2 entry
        if parts[0] == 'pbkdf2_sha256' and len(parts) >= 4:
            try:
                # Try to parse as valid PBKDF2 (strict check for integrity)
                # Handle comma-formatted iteration counts (e.g., "100,000")
                iterations_str = parts[1].replace(',', '')
                int(iterations_str)

                # Validate base64 components
                if parts[2]:  # salt can be empty
                    base64.b64decode(parts[2])
                base64.b64decode(parts[3])

                valid_pbkdf2_count += 1
                valid_usernames.add(username)
            except (ValueError, IndexError, base64.binascii.Error):
                # Malformed PBKDF2 entry (e.g., bad base64, comma in iterations)
                malformed_count += 1
        else:
            # Non-PBKDF2 format (bcrypt, argon2, etc.)
            malformed_count += 1

    # The oracle generates exactly EXPECTED_VALID_HASHES valid PBKDF2 entries
    assert valid_pbkdf2_count == EXPECTED_VALID_HASHES, \
        f"Expected exactly {EXPECTED_VALID_HASHES} valid PBKDF2 entries, found {valid_pbkdf2_count}. " \
        f"File may have been tampered with."

    # The oracle inserts exactly EXPECTED_MALFORMED_HASHES malformed entries
    assert malformed_count == EXPECTED_MALFORMED_HASHES, \
        f"Expected exactly {EXPECTED_MALFORMED_HASHES} malformed entries, found {malformed_count}. " \
        f"File may have been tampered with."

    # Verify usernames follow expected pattern (user001-user010)
    # The oracle generates user001-user021 explicitly, then extends to [:10] giving us user001-user010
    expected_users = {f'user{i:03d}' for i in range(1, 11)}
    assert valid_usernames == expected_users, \
        f"Username set doesn't match expected pattern. " \
        f"Missing: {expected_users - valid_usernames}, " \
        f"Extra: {valid_usernames - expected_users}. " \
        f"File may have been tampered with."

    # Verify a specific hash to bind the content to known ground truth (anti-cheating)
    # user001 has empty salt (i=0, 0 % 17 == 0), iterations=1000, password=Password123
    # user001:pbkdf2_sha256$1000$$SDBFZqLqPdgnL0lEuDGZS9fuIzRfv2pthaxtn1mlfto=
    known_hash = "user001:pbkdf2_sha256$1000$$SDBFZqLqPdgnL0lEuDGZS9fuIzRfv2pthaxtn1mlfto="
    assert any(known_hash in line for line in lines), \
        "Hash file content mismatch. Do not modify the input hashes file."


def test_mangling_rules_were_applied():
    """Verify that password mangling rules were likely applied."""
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')
    csv_lines = lines[1:]  # Skip canary
    reader = csv.DictReader(csv_lines)
    cracked = list(reader)

    passwords = [row['password'] for row in cracked]

    # Check for evidence of mangling rules
    has_capitalization = any(p[0].isupper() for p in passwords if p)
    has_numbers = any(any(c.isdigit() for c in p) for p in passwords)
    has_symbols = any(any(c in '!@#$' for c in p) for p in passwords)

    mangling_indicators = sum([has_capitalization, has_numbers, has_symbols])

    assert mangling_indicators >= 2, \
        "Password list should show evidence of mangling rules (capitalization, numbers, symbols)"


def test_robust_parsing():
    """Verify solution handles malformed entries gracefully without crashing."""
    # This test passes if the output file exists and is valid
    # Even with malformed entries in the input
    output_path = Path("/app/cracked.csv")
    assert output_path.exists(), "Output file must exist despite malformed input entries"

    # Verify output is valid CSV
    content = output_path.read_text()
    assert "CRACKED_BY_TERMINUS_AGENT_2026" in content, "Output must contain canary"
    assert "username,password" in content, "Output must contain CSV header"

    # Parse and verify at least some passwords were cracked
    lines = content.strip().split('\n')
    csv_lines = lines[1:]
    reader = csv.DictReader(csv_lines)
    rows = list(reader)

    assert len(rows) > 0, "Solution must crack at least some passwords despite malformed entries"


def test_input_has_multiple_iteration_counts():
    """Verify test data includes multiple iteration counts (for clustering validation)."""
    hashes_path = Path("/app/hashes.txt")
    assert hashes_path.exists(), "Input hashes file must exist"

    iteration_counts = set()
    for line in hashes_path.read_text().strip().split('\n'):
        if not line or ':pbkdf2_sha256$' not in line:
            continue

        try:
            parts = line.split('$')
            if len(parts) >= 2:
                # Handle comma-formatted iterations
                iterations_str = parts[1].replace(',', '')
                iterations = int(iterations_str)
                iteration_counts.add(iterations)
        except (ValueError, IndexError):
            # Skip malformed entries
            continue

    assert len(iteration_counts) >= 2, \
        "Test data should contain at least 2 different iteration counts for clustering"


def test_reasonable_crack_rate():
    """Verify a reasonable number of passwords were cracked."""
    hashes_path = Path("/app/hashes.txt")
    all_lines = hashes_path.read_text().strip().split('\n')

    # Count only valid PBKDF2 hashes (skip malformed entries)
    valid_hashes = 0
    for line in all_lines:
        if line and ':pbkdf2_sha256$' in line:
            parts = line.split('$')
            # Basic validation: should have at least 4 parts
            if len(parts) >= 4:
                valid_hashes += 1

    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')
    csv_lines = lines[1:]  # Skip canary
    reader = csv.DictReader(csv_lines)
    cracked_count = len(list(reader))

    # Should crack at least 30% of valid hashes (harder passwords)
    assert cracked_count >= valid_hashes * 0.3, \
        f"Expected to crack at least 30% of valid hashes, got {cracked_count}/{valid_hashes}"


def test_completion_within_timeout():
    """
    Verify solution completes within the 15-minute timeout requirement.

    This test checks that the output file's modification time is recent enough
    to indicate the solution ran and completed. The actual timeout enforcement
    happens at the environment/container level.
    """
    import time

    output_path = Path("/app/cracked.csv")
    assert output_path.exists(), "Output file must exist (solution may have timed out)"

    # Check file was modified recently (within last 15 minutes)
    # This validates solution completed in reasonable time
    mtime = output_path.stat().st_mtime
    current_time = time.time()
    age_seconds = current_time - mtime
    age_minutes = age_seconds / 60

    assert age_minutes <= 15, \
        f"Output file is {age_minutes:.1f} minutes old - solution may have exceeded timeout"


def test_absolute_paths_used():
    """
    Verify solution uses absolute paths as required by specification.

    The instruction explicitly requires: "Use absolute paths: /app/hashes.txt,
    /app/dictionary.txt, /app/cracked.csv"

    This test validates the solution correctly places output at the absolute path.
    """
    # The specification requires /app/cracked.csv (absolute path)
    output_path = Path("/app/cracked.csv")

    assert output_path.exists(), \
        "Output must exist at absolute path /app/cracked.csv as specified in requirements"

    assert output_path.is_absolute(), \
        "Output path /app/cracked.csv must be absolute"

    # Verify it's not a symlink to a relative path (anti-cheat)
    assert not output_path.is_symlink() or output_path.resolve().is_absolute(), \
        "Output must be at true absolute path, not symlinked to relative location"


def test_comprehensive_transformations():
    """
    Verify solution applies comprehensive password transformations.

    The instruction requires: "Your transformations should be comprehensive enough
    to crack challenging passwords that combine multiple modification patterns."

    This test validates that the solution cracks passwords with COMBINED transformations,
    not just simple single-rule modifications.
    """
    output_path = Path("/app/cracked.csv")
    lines = output_path.read_text().strip().split('\n')
    csv_lines = lines[1:]  # Skip canary
    reader = csv.DictReader(csv_lines)
    cracked = list(reader)

    passwords = [row['password'] for row in cracked]

    # Track evidence of COMBINED transformations (multiple rules applied)
    combined_transformations = 0

    for pwd in passwords:
        transformation_count = 0

        # Check for capitalization (first letter uppercase, rest lowercase)
        if pwd and pwd[0].isupper() and any(c.islower() for c in pwd[1:]):
            transformation_count += 1

        # Check for all caps
        if pwd and pwd.isupper():
            transformation_count += 1

        # Check for digits
        if any(c.isdigit() for c in pwd):
            transformation_count += 1

        # Check for symbols
        if any(c in '!@#$' for c in pwd):
            transformation_count += 1

        # Check for leet speak patterns (common substitutions)
        leet_patterns = ['@', '3', '0', '1', '$', '7']
        if any(pattern in pwd for pattern in leet_patterns):
            # Only count if it's combined with other transformations
            if transformation_count > 0:
                transformation_count += 1

        # Password combines 2+ transformation types = comprehensive
        if transformation_count >= 2:
            combined_transformations += 1

    # At least 40% of cracked passwords should show combined transformations
    # This validates the solution handles complex passwords, not just simple ones
    combined_rate = combined_transformations / len(passwords) if passwords else 0

    assert combined_rate >= 0.4, \
        f"Only {combined_transformations}/{len(passwords)} ({combined_rate:.1%}) passwords show " \
        f"combined transformations. Solution must handle complex multi-rule passwords " \
        f"(e.g., 'P@ssw0rd123!' requires capitalize + leet + numbers + symbols)."
