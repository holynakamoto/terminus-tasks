#!/usr/bin/env python3
"""
⚠️ TEST DATA GENERATION ONLY - DO NOT USE IN PRODUCTION ⚠️

This script generates INTENTIONALLY WEAK test data for educational purposes.
The iteration counts (max 50,000) are 12x LESS than OWASP 2023 recommendations
(600,000+ for PBKDF2-SHA256). Production systems MUST use secure parameters.

Generate test data for the cracked256 password cracking task.
This runs at Docker image build time (via RUN in Dockerfile) and creates hashes.txt
and dictionary.txt that are baked into the image for agents to work with.
"""
import hashlib
import base64
import random

# Constants matching test expectations
EXPECTED_VALID_HASHES = 10  # Must match test_outputs.py (minimal viable for sub-30min pipeline)
EXPECTED_MALFORMED_HASHES = 3  # Must match test_outputs.py
EXTENDED_PATTERN_COUNT = 20  # Generate extra patterns, use first 10

# Base dictionary words (reduced to 12 for faster eval times)
base_words = [
    'password', 'admin', 'secret', 'test', 'hello', 'welcome',
    'master', 'dragon', 'monkey', 'letmein', 'football', 'iloveyou'
]

# Create passwords that require COMBINED mangling rules
# Format: (username, base_word, transformations_needed)
password_patterns = [
    # Capitalize + number suffix
    ('user001', 'password', 'Password123'),
    ('user002', 'admin', 'Admin2024'),
    ('user003', 'secret', 'Secret999'),

    # Leet speak + number
    ('user004', 'password', 'p@ssw0rd123'),
    ('user005', 'admin', '@dm1n456'),

    # Capitalize + leet + symbol
    ('user006', 'password', 'P@ssw0rd!'),
    ('user007', 'test', 'T3st@'),

    # All caps + symbol
    ('user008', 'hello', 'HELLO!'),
    ('user009', 'welcome', 'WELCOME@'),

    # Complex: capitalize + leet + number + symbol
    ('user010', 'password', 'P@ssw0rd123!'),
    ('user011', 'master', 'M@st3r2024#'),

    # Just capitalize
    ('user012', 'dragon', 'Dragon'),
    ('user013', 'monkey', 'Monkey'),

    # Base word only
    ('user014', 'football', 'football'),
    ('user015', 'sunshine', 'sunshine'),

    # Year suffixes (must try current/recent years)
    ('user016', 'password', 'Password2026'),
    ('user017', 'admin', 'Admin2025'),

    # Multiple leet substitutions
    ('user018', 'letmein', 'l3tm31n'),
    ('user019', 'iloveyou', '1l0v3y0u'),

    # Capitalization patterns
    ('user020', 'starwars', 'StarWars'),
    ('user021', 'princess', 'PRINCESS123'),
]

# Extend to EXTENDED_PATTERN_COUNT users with variations
random.seed(42)  # Deterministic for reproducibility
for i in range(len(password_patterns) + 1, EXTENDED_PATTERN_COUNT + 1):
    base = random.choice(base_words)
    transforms = random.choice([
        base,
        base.capitalize(),
        base + '123',
        base.upper() + '!',
        base.capitalize() + str(random.randint(2020, 2026)),
    ])
    password_patterns.append((f'user{i:03d}', base, transforms))

# OPTIMIZED FOR SUB-30MIN PIPELINE: Minimal viable task
# Max 10000 iterations, only 10 hashes
# Distribution: 10 values cycling through 3 levels
iteration_counts = [
    1000, 1000, 1000,      # Low (3)
    5000, 5000, 5000,      # Medium (3)
    10000, 10000, 10000, 10000, # High (4)
]

hashes = []

print(f"Generating {EXPECTED_VALID_HASHES} password hashes...")

# Generate valid hashes
for i, (username, base_word, password) in enumerate(password_patterns[:EXPECTED_VALID_HASHES]):
    iterations = iteration_counts[i % len(iteration_counts)]  # Use modulo to cycle through counts

    # Some entries have empty salts (edge case) - creates 4 empty salts at indices 0, 17, 34, 51
    if i % 17 == 0:
        salt = b''
        salt_b64 = ''
    else:
        salt = f"salt{i}".encode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')

    # Generate PBKDF2-HMAC-SHA256 hash
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')

    hash_line = f"{username}:pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"
    hashes.append(hash_line)

# Add malformed entries (debugging traps) - inserted at specific positions to test error handling
malformed_entries = [
    (8, "baduser3:pbkdf2_sha256$50000$c2FsdA!!!$dGVzdGhhc2g="),  # Invalid base64
    (5, "baduser2:pbkdf2_sha256$10000$c2FsdA=="),  # Missing hash component
    (2, "baduser1:pbkdf2_sha256$100,000x$c2FsdA$aGFzaA=="),  # Invalid iteration count
]

for position, entry in malformed_entries:
    hashes.insert(position, entry)

# Write hashes to file
with open('/app/hashes.txt', 'w') as f:
    f.write('\n'.join(hashes) + '\n')

# Create dictionary with ONLY base words (no mangling)
with open('/app/dictionary.txt', 'w') as f:
    f.write('\n'.join(base_words) + '\n')

print(f"Generated {len(hashes)} hash entries ({len([h for h in hashes if 'baduser' in h])} malformed)")
print(f"Generated {len(base_words)} base dictionary words")
print(f"Iteration counts used: {sorted(set(iteration_counts))}")
print("Test data ready at /app/hashes.txt and /app/dictionary.txt")
