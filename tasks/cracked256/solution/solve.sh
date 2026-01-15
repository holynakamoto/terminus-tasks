#!/bin/bash
set -euo pipefail

# Generate challenging test data with edge cases and debugging traps
python3 << 'GENERATE_DATA'
import hashlib
import base64
import random
import os

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
    ('user020', 'starwars', 'StarWars'),  # Capital first letters of compound
    ('user021', 'princess', 'PRINCESS123'),
]

# Extend to 70+ users with variations
for i in range(22, 75):
    base = random.choice(base_words)
    # Random transformation pattern
    transforms = random.choice([
        base,  # No transform
        base.capitalize(),  # Simple capitalize
        base + '123',  # Number suffix
        base.upper() + '!',  # Uppercase + symbol
        base.capitalize() + str(random.randint(2020, 2026)),  # Year suffix
    ])
    password_patterns.append((f'user{i:03d}', base, transforms))

# Create hashes with varying iteration counts (force clustering optimization)
iteration_counts = [
    1000, 1000, 1000,  # Low iterations
    10000, 10000, 10000, 10000, 10000,  # Medium-low
    50000, 50000, 50000, 50000,  # Medium
    100000, 100000, 100000, 100000, 100000,  # Medium-high
    200000, 200000, 200000,  # High
    500000, 500000,  # Very high (forces optimization)
]

hashes = []

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

    # Format: username:pbkdf2_sha256$iterations$salt$hash
    hash_line = f"{username}:pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"
    hashes.append(hash_line)

# Add malformed entries (debugging traps)
# These should be skipped gracefully

# Trap 1: Iteration count formatted with comma (common export error)
malformed1 = "baduser1:pbkdf2_sha256$100,000$c2FsdA==$aGFzaA=="
hashes.insert(10, malformed1)

# Trap 2: Missing hash component
malformed2 = "baduser2:pbkdf2_sha256$10000$c2FsdA=="
hashes.insert(25, malformed2)

# Trap 3: Invalid base64 in salt (contains invalid character)
malformed3 = "baduser3:pbkdf2_sha256$50000$c2Fsd@$dGVzdGhhc2g="
hashes.insert(40, malformed3)

# Trap 4: Unknown hash algorithm (should skip)
malformed4 = "baduser4:bcrypt$12$c2FsdDEyMzQ=$aGFzaGRhdGE="
hashes.insert(55, malformed4)

# Trap 5: Argon2 format (mentioned in instructions but not in test)
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
print("Agents must discover and apply mangling rules to crack passwords")
GENERATE_DATA

# Oracle solution: comprehensive cracker with all optimizations
python3 << 'CRACKER_SCRIPT'
import hashlib
import base64
import csv
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import re

def parse_hash_line(line):
    """Parse a hash line and extract components, with robust error handling."""
    line = line.strip()
    if not line:
        return None

    try:
        username, hash_part = line.split(':', 1)
    except ValueError:
        return None

    parts = hash_part.split('$')

    # Only handle PBKDF2-SHA256
    if len(parts) < 4 or parts[0] != 'pbkdf2_sha256':
        return None

    try:
        # Handle comma-formatted iteration counts
        iterations_str = parts[1].replace(',', '')
        iterations = int(iterations_str)

        salt_b64 = parts[2]
        hash_b64 = parts[3]

        # Handle empty salt
        if salt_b64:
            salt = base64.b64decode(salt_b64)
        else:
            salt = b''

        target_hash = base64.b64decode(hash_b64)

        return {
            'username': username,
            'iterations': iterations,
            'salt': salt,
            'target_hash': target_hash,
        }
    except (ValueError, base64.binascii.Error):
        # Malformed entry, skip
        return None

def generate_mangled_passwords(base_word):
    """Generate comprehensive mangled variations."""
    candidates = set()

    # Original
    candidates.add(base_word)

    # Capitalize first letter
    candidates.add(base_word.capitalize())

    # All uppercase
    candidates.add(base_word.upper())

    # Common suffixes
    suffixes = ['1', '12', '123', '456', '789', '1234', '!', '@', '#', '$', '!!']
    years = ['2020', '2021', '2022', '2023', '2024', '2025', '2026']

    for suffix in suffixes + years:
        candidates.add(base_word + suffix)
        candidates.add(base_word.capitalize() + suffix)
        candidates.add(base_word.upper() + suffix)

    # Leet speak substitutions
    leet_map = {
        'a': ['@', '4'],
        'e': ['3'],
        'i': ['1', '!'],
        'o': ['0'],
        's': ['$', '5'],
        't': ['7'],
        'l': ['1'],
    }

    # Generate leet variations
    def apply_leet(word, aggressive=False):
        result = word
        for char, replacements in leet_map.items():
            if char in result:
                for repl in replacements:
                    result = result.replace(char, repl)
                    if not aggressive:
                        break  # Only apply first substitution per char
        return result

    leet_word = apply_leet(base_word)
    if leet_word != base_word:
        candidates.add(leet_word)
        candidates.add(leet_word.capitalize())

        # Leet + common suffixes
        for suffix in ['123', '456', '!', '@', '#']:
            candidates.add(leet_word + suffix)
            candidates.add(leet_word.capitalize() + suffix)

    # Complex combinations: capitalize + leet + number + symbol
    leet_cap = apply_leet(base_word.capitalize())
    for num in ['123', '456', '789', '999', '2024', '2025', '2026']:
        for sym in ['!', '@', '#']:
            candidates.add(leet_cap + num + sym)
            candidates.add(leet_word + num + sym)

    # Title case for compound words
    if len(base_word) > 6:
        # Try capitalizing multiple positions
        for i in range(1, len(base_word)):
            title_case = base_word[:i].capitalize() + base_word[i:].capitalize()
            if title_case != base_word.capitalize():
                candidates.add(title_case)

    return list(candidates)

def crack_cluster(cluster_data):
    """
    Crack a cluster of hashes with the same iteration count.
    This optimization is CRITICAL for performance.
    """
    iterations, hash_list, password_candidates = cluster_data
    results = []

    # Build lookup table
    hash_lookup = {}
    for hash_info in hash_list:
        key = (hash_info['salt'], hash_info['target_hash'])
        hash_lookup[key] = hash_info['username']

    # Get unique salts
    salts_in_cluster = set(h['salt'] for h in hash_list)

    for password in password_candidates:
        password_bytes = password.encode('utf-8')

        # Hash with each unique salt
        for salt in salts_in_cluster:
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password_bytes,
                salt,
                iterations
            )

            key = (salt, computed_hash)
            if key in hash_lookup:
                username = hash_lookup[key]
                results.append({
                    'username': username,
                    'password': password
                })

    return results

# Read hashes file
with open('/app/hashes.txt', 'r') as f:
    hash_lines = f.readlines()

# Parse and cluster by iteration count (CRITICAL optimization)
clusters = defaultdict(list)
parsed_count = 0
skipped_count = 0

for line in hash_lines:
    hash_info = parse_hash_line(line)
    if hash_info:
        clusters[hash_info['iterations']].append(hash_info)
        parsed_count += 1
    else:
        skipped_count += 1

print(f"Parsed {parsed_count} valid hashes, skipped {skipped_count} malformed entries")
print(f"Clustered into {len(clusters)} iteration groups: {list(clusters.keys())}")

# Read dictionary and generate mangled passwords
with open('/app/dictionary.txt', 'r') as f:
    base_words = [line.strip() for line in f if line.strip()]

all_candidates = []
for word in base_words:
    all_candidates.extend(generate_mangled_passwords(word))

# Remove duplicates
all_candidates = list(set(all_candidates))

print(f"Generated {len(all_candidates)} unique password candidates from {len(base_words)} base words")

# Prepare cluster data for parallel processing
cluster_tasks = [
    (iterations, hash_list, all_candidates)
    for iterations, hash_list in clusters.items()
]

# Crack hashes in parallel across clusters
cracked = []
cpu_count = max(1, os.cpu_count() or 1)

with ProcessPoolExecutor(max_workers=min(cpu_count, len(cluster_tasks))) as executor:
    futures = {
        executor.submit(crack_cluster, task): task[0]
        for task in cluster_tasks
    }

    for future in as_completed(futures):
        iterations = futures[future]
        cluster_results = future.result()

        if cluster_results:
            cracked.extend(cluster_results)
            print(f"Cluster {iterations}: cracked {len(cluster_results)} passwords")

# Sort by username
cracked.sort(key=lambda x: x['username'])

# Write output
with open('/app/cracked.csv', 'w') as f:
    f.write('CRACKED_BY_TERMINUS_AGENT_2026\n')
    writer = csv.DictWriter(f, fieldnames=['username', 'password'])
    writer.writeheader()
    writer.writerows(cracked)

print(f"\nSuccessfully cracked {len(cracked)} passwords")
print(f"Output written to /app/cracked.csv")
CRACKER_SCRIPT
