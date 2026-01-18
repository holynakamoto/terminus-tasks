#!/usr/bin/env python3
"""
Generate test data for the cracked256 password cracking task.
This runs on container startup to create hashes.txt and dictionary.txt for agents to work with.
"""
import hashlib
import base64
import random

# Base dictionary words
base_words = [
    'password', 'admin', 'secret', 'test', 'hello', 'welcome', 'master',
    'summer', 'dragon', 'monkey', 'letmein', 'football', 'iloveyou',
    'starwars', 'sunshine', 'princess', 'batman', 'trustno', 'freedom'
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

# Extend to 70+ users with variations
random.seed(42)  # Deterministic for reproducibility
for i in range(22, 75):
    base = random.choice(base_words)
    transforms = random.choice([
        base,
        base.capitalize(),
        base + '123',
        base.upper() + '!',
        base.capitalize() + str(random.randint(2020, 2026)),
    ])
    password_patterns.append((f'user{i:03d}', base, transforms))

# OPTIMIZED FOR 1 CPU: Lower iteration counts
# Max 50000 instead of 500000 (10x reduction)
iteration_counts = [
    1000, 1000, 1000, 1000, 1000,      # Low (5)
    5000, 5000, 5000, 5000, 5000,      # Low-medium (5)
    10000, 10000, 10000, 10000, 10000, # Medium (5)
    20000, 20000, 20000, 20000, 20000, # Medium-high (5)
    50000, 50000,                       # High (2) - max iteration count
]

hashes = []

print(f"Generating {len(password_patterns[:60])} password hashes...")

# Generate valid hashes
for i, (username, base_word, password) in enumerate(password_patterns[:60]):
    iterations = iteration_counts[i % len(iteration_counts)]

    # Some entries have empty salts (edge case)
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

# Add malformed entries (debugging traps)
# malformed1: Use invalid iteration count (with 'x') to ensure it's not counted as valid
malformed1 = "baduser1:pbkdf2_sha256$100,000x$c2FsdA$aGFzaA=="
hashes.insert(10, malformed1)

malformed2 = "baduser2:pbkdf2_sha256$10000$c2FsdA=="
hashes.insert(25, malformed2)

# malformed3: Use invalid base64 character (!) to ensure it's not counted as valid
malformed3 = "baduser3:pbkdf2_sha256$50000$c2FsdA!!!$dGVzdGhhc2g="
hashes.insert(40, malformed3)

malformed4 = "baduser4:bcrypt$12$c2FsdDEyMzQ=$aGFzaGRhdGE="
hashes.insert(55, malformed4)

malformed5 = "baduser5:argon2$m=65536,t=3,p=4$c2FsdA==$aGFzaA=="
hashes.insert(30, malformed5)

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
