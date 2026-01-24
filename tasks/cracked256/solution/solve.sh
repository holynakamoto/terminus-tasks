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

# ============================================================
# ENVIRONMENT DETECTION
# Explicit mode selection via EVAL_MODE environment variable
# ============================================================
# EVAL_MODE values:
#   - "snorkel": Use pre-generated data (fast builds, production eval)
#   - "github":  Generate at runtime (flexible, CI/CD)
#   - "auto":    Auto-detect based on file presence (default)
EVAL_MODE=${EVAL_MODE:-auto}

echo "[DEBUG] Environment mode: $EVAL_MODE"

# Determine if we should use pre-generated data
USE_PREGENERATED=false

if [ "$EVAL_MODE" = "snorkel" ]; then
    USE_PREGENERATED=true
    echo "[DEBUG] Explicit Snorkel mode - using pre-generated data"
elif [ "$EVAL_MODE" = "github" ]; then
    USE_PREGENERATED=false
    echo "[DEBUG] Explicit GitHub mode - generating data at runtime"
elif [ "$EVAL_MODE" = "auto" ]; then
    if [ -f /app/hashes.txt ] && [ -f /app/dictionary.txt ]; then
        USE_PREGENERATED=true
        echo "[DEBUG] Auto-detected Snorkel environment (data files present)"
    else
        USE_PREGENERATED=false
        echo "[DEBUG] Auto-detected GitHub environment (no data files)"
    fi
else
    echo "[ERROR] Invalid EVAL_MODE: $EVAL_MODE (expected: snorkel|github|auto)"
    exit 1
fi

# ============================================================
# CONDITIONAL DATA GENERATION
# ============================================================
if [ "$USE_PREGENERATED" = "true" ]; then
    echo "[DEBUG] Using pre-generated data files"
    echo "[DEBUG] hashes.txt: $(wc -l < /app/hashes.txt) lines"
    echo "[DEBUG] dictionary.txt: $(wc -l < /app/dictionary.txt) lines"
else
    # Generate challenging test data with edge cases and debugging traps
    echo "[DEBUG] Generating data at runtime"
    echo "[DEBUG] Starting data generation at $(date -Iseconds)"
    python3 << 'GENERATE_DATA'
import hashlib
import base64
import random
import time

start = time.time()
print(f"[DEBUG] Python data generation started")

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

# OPTIMIZED FOR SUB-30MIN PIPELINE: Minimal viable task
# Max 10000 iterations, only 10 hashes
iteration_counts = [
    1000, 1000, 1000,      # Low (3)
    5000, 5000, 5000,      # Medium (3)
    10000, 10000, 10000, 10000, # High (4)
]

hashes = []

print(f"[DEBUG] Generating {len(password_patterns[:10])} password hashes...")

# Generate valid hashes
for i, (username, base_word, password) in enumerate(password_patterns[:10]):
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
    echo "[DEBUG] Runtime data generation completed at $(date -Iseconds)"
    echo "[DEBUG] Data generation took $((DATA_GEN_TIME - START_TIME)) seconds"
fi

# Display data file info (works for both pre-generated and runtime-generated)
echo "[DEBUG] Final data files:"
echo "[DEBUG] - hashes.txt: $(wc -l < /app/hashes.txt) lines, $(stat -c%s /app/hashes.txt 2>/dev/null || stat -f%z /app/hashes.txt 2>/dev/null || echo 'unknown') bytes"
echo "[DEBUG] - dictionary.txt: $(wc -l < /app/dictionary.txt) lines"

# Oracle solution: optimized cracker
echo "[DEBUG] Starting password cracker at $(date -Iseconds)"

# Copy cracker script to /app if running from solution directory
if [ -f "$(dirname "$0")/crack_passwords.py" ]; then
    cp "$(dirname "$0")/crack_passwords.py" /tmp/crack_passwords.py
    CRACKER_SCRIPT="/tmp/crack_passwords.py"
elif [ -f "/solution/crack_passwords.py" ]; then
    CRACKER_SCRIPT="/solution/crack_passwords.py"
else
    echo "[ERROR] crack_passwords.py not found"
    exit 1
fi

# Run the cracker with environment variables
export CPUS=${CPUS:-1}
export PARALLEL_CRACKING=${PARALLEL_CRACKING:-false}

python3 "$CRACKER_SCRIPT"


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
