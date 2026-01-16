#!/bin/bash
set -euo pipefail

# ============================================================
# DEBUGGING: Print environment and timing info
# ============================================================
echo "============================================================"
echo "[DEBUG] Oracle solve.sh starting at $(date -Iseconds)"
echo "[DEBUG] Hostname: $(hostname)"
echo "[DEBUG] CPU info: $(nproc) cores available"
echo "[DEBUG] Memory info: $(free -h 2>/dev/null | head -2 || echo 'free command not available')"
echo "[DEBUG] Working directory: $(pwd)"
echo "[DEBUG] Disk space: $(df -h /app 2>/dev/null | tail -1 || echo 'df not available')"
echo "============================================================"

START_TIME=$(date +%s)

# Generate challenging test data with edge cases and debugging traps
echo "[DEBUG] Starting data generation at $(date -Iseconds)"
python3 << 'GENERATE_DATA'
import hashlib
import base64
import random
import time

start = time.time()
print(f"[DEBUG] Python data generation started")

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

print(f"[DEBUG] Generating {len(password_patterns[:60])} password hashes...")

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

elapsed = time.time() - start
print(f"[DEBUG] Generated {len(hashes)} hash entries ({len([h for h in hashes if 'baduser' in h])} malformed)")
print(f"[DEBUG] Generated {len(base_words)} base dictionary words")
print(f"[DEBUG] Iteration counts used: {sorted(set(iteration_counts))}")
print(f"[DEBUG] Data generation completed in {elapsed:.2f}s")
GENERATE_DATA

DATA_GEN_TIME=$(date +%s)
echo "[DEBUG] Data generation completed at $(date -Iseconds)"
echo "[DEBUG] Data generation took $((DATA_GEN_TIME - START_TIME)) seconds"

# Oracle solution: optimized cracker for 1 CPU
echo "[DEBUG] Starting password cracker at $(date -Iseconds)"
python3 << 'CRACKER_SCRIPT'
import hashlib
import base64
import csv
from collections import defaultdict
import time
import sys

overall_start = time.time()
print(f"[DEBUG] Cracker script started")
print(f"[DEBUG] Python version: {sys.version}")

def log_progress(msg):
    elapsed = time.time() - overall_start
    print(f"[DEBUG] [{elapsed:7.1f}s] {msg}")

def parse_hash_line(line):
    """Parse a hash line with robust error handling."""
    line = line.strip()
    if not line:
        return None

    try:
        username, hash_part = line.split(':', 1)
    except ValueError:
        return None

    parts = hash_part.split('$')

    if len(parts) < 4 or parts[0] != 'pbkdf2_sha256':
        return None

    try:
        iterations_str = parts[1].replace(',', '')
        iterations = int(iterations_str)
        salt_b64 = parts[2]
        hash_b64 = parts[3]

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
        return None

def generate_mangled_passwords(base_word):
    """Generate mangled variations - OPTIMIZED for fewer candidates."""
    candidates = set()

    # Original and basic transforms
    candidates.add(base_word)
    candidates.add(base_word.capitalize())
    candidates.add(base_word.upper())

    # Common suffixes (reduced set)
    suffixes = ['123', '456', '999', '!', '@', '#']
    years = ['2024', '2025', '2026']

    for suffix in suffixes + years:
        candidates.add(base_word + suffix)
        candidates.add(base_word.capitalize() + suffix)
        candidates.add(base_word.upper() + suffix)

    # Leet speak
    leet_map = {'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '$'}
    
    def apply_leet(word):
        result = word
        for char, repl in leet_map.items():
            result = result.replace(char, repl)
        return result

    leet_word = apply_leet(base_word)
    if leet_word != base_word:
        candidates.add(leet_word)
        for suffix in ['123', '456', '!']:
            candidates.add(leet_word + suffix)

    # Capitalize + leet combinations
    leet_cap = apply_leet(base_word.capitalize())
    for num in ['123', '2024', '2025', '2026']:
        for sym in ['!', '@', '#']:
            candidates.add(leet_cap + num + sym)
            candidates.add(leet_word + num + sym)

    # Title case for compound words
    if len(base_word) > 6:
        mid = len(base_word) // 2
        title_case = base_word[:mid].capitalize() + base_word[mid:].capitalize()
        candidates.add(title_case)

    return list(candidates)

# Read and parse hashes
log_progress("Reading hashes file...")
with open('/app/hashes.txt', 'r') as f:
    hash_lines = f.readlines()

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

log_progress(f"Parsed {parsed_count} valid hashes, skipped {skipped_count} malformed")
log_progress(f"Iteration clusters: {sorted(clusters.keys())}")

# Read dictionary and generate candidates
log_progress("Generating password candidates...")
with open('/app/dictionary.txt', 'r') as f:
    base_words = [line.strip() for line in f if line.strip()]

all_candidates = set()
for word in base_words:
    all_candidates.update(generate_mangled_passwords(word))

all_candidates = list(all_candidates)
log_progress(f"Generated {len(all_candidates)} unique candidates from {len(base_words)} base words")

# SEQUENTIAL cracking (optimized for 1 CPU)
cracked = []
total_hashes = sum(len(h) for h in clusters.values())
cracked_so_far = 0

# Process clusters in order of iteration count (fastest first)
for iterations in sorted(clusters.keys()):
    hash_list = clusters[iterations]
    cluster_start = time.time()
    
    log_progress(f"Processing cluster iterations={iterations} ({len(hash_list)} hashes)...")
    
    # Build lookup table
    hash_lookup = {}
    for hash_info in hash_list:
        key = (hash_info['salt'], hash_info['target_hash'])
        hash_lookup[key] = hash_info['username']
    
    salts_in_cluster = list(set(h['salt'] for h in hash_list))
    cluster_cracked = 0
    
    for idx, password in enumerate(all_candidates):
        password_bytes = password.encode('utf-8')
        
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
                cracked.append({'username': username, 'password': password})
                cluster_cracked += 1
                del hash_lookup[key]  # Remove to avoid duplicates
        
        # Progress every 500 candidates
        if (idx + 1) % 500 == 0:
            elapsed = time.time() - cluster_start
            log_progress(f"  Cluster {iterations}: {idx+1}/{len(all_candidates)} candidates, {cluster_cracked} cracked, {elapsed:.1f}s")
    
    cluster_elapsed = time.time() - cluster_start
    cracked_so_far += cluster_cracked
    log_progress(f"Cluster {iterations} done: {cluster_cracked} cracked in {cluster_elapsed:.1f}s (total: {cracked_so_far})")

# Sort and write output
log_progress("Writing output file...")
cracked.sort(key=lambda x: x['username'])

with open('/app/cracked.csv', 'w') as f:
    f.write('CRACKED_BY_TERMINUS_AGENT_2026\n')
    writer = csv.DictWriter(f, fieldnames=['username', 'password'])
    writer.writeheader()
    writer.writerows(cracked)

total_elapsed = time.time() - overall_start
log_progress(f"COMPLETED: Cracked {len(cracked)}/{parsed_count} passwords ({100*len(cracked)/parsed_count:.1f}%)")
log_progress(f"Total cracking time: {total_elapsed:.1f}s")
print(f"\n[DEBUG] Output written to /app/cracked.csv")
print(f"[DEBUG] First 5 entries: {cracked[:5]}")
CRACKER_SCRIPT

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo "============================================================"
echo "[DEBUG] Oracle solve.sh completed at $(date -Iseconds)"
echo "[DEBUG] Total execution time: ${TOTAL_TIME} seconds"
echo "[DEBUG] Output file size: $(ls -la /app/cracked.csv 2>/dev/null || echo 'FILE NOT FOUND')"
echo "[DEBUG] Output file head:"
head -10 /app/cracked.csv 2>/dev/null || echo "[DEBUG] Could not read output file"
echo "[DEBUG] Output file line count: $(wc -l < /app/cracked.csv 2>/dev/null || echo 'N/A')"
echo "============================================================"
