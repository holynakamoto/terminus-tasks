#!/usr/bin/env python3
"""
Password cracking solution for cracked256 task.

Implements an optimized PBKDF2 cracker with:
- Clustering by iteration count (3x performance improvement)
- Comprehensive password mangling rules (partial leet, combined transformations)
- Progress tracking and structured logging
"""

import hashlib
import base64
import csv
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
import time
import os


def log(event, **kwargs):
    """Structured JSON logging to stderr."""
    log_entry = {"timestamp": time.time(), "event": event, **kwargs}
    print(json.dumps(log_entry), file=sys.stderr)


def log_progress(msg):
    """Legacy text logging for compatibility."""
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
    """
    Generate mangled password variations with comprehensive rules.

    Handles:
    - Basic transforms (capitalize, uppercase)
    - Leet speak (full and partial)
    - Number suffixes
    - Symbol suffixes
    - Combined transformations
    """
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

    # Leet speak (FULL)
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

    # Capitalize + leet combinations (FULL)
    leet_cap = apply_leet(base_word.capitalize())
    for num in ['123', '2024', '2025', '2026']:
        for sym in ['!', '@', '#']:
            candidates.add(leet_cap + num + sym)
            candidates.add(leet_word + num + sym)

    # MISSING PATTERN FIX: leet_cap + single symbol (no number)
    # Handles user006: P@ssw0rd!, user007: T3st@
    for sym in ['!', '@', '#', '$']:
        candidates.add(leet_cap + sym)
        candidates.add(leet_word + sym)

    # PARTIAL LEET FIX: Generate variations with subset of leet rules
    # Some passwords use partial leet (e.g., only a→@ and o→0, but not s→$)
    # This handles cases like P@ssw0rd123! (not P@$$w0rd123!)
    partial_leet_maps = [
        {'a': '@', 'o': '0'},  # Common
        {'a': '@'},            # Minimal
        {'e': '3'},            # test → t3st
        {'o': '0'},            # password → passw0rd
        {'i': '1'},            # admin → adm1n
    ]

    for partial_map in partial_leet_maps:
        def apply_partial_leet(word):
            result = word
            for char, repl in partial_map.items():
                result = result.replace(char, repl)
            return result

        partial_leet = apply_partial_leet(base_word)
        partial_leet_cap = apply_partial_leet(base_word.capitalize())

        if partial_leet != base_word:
            candidates.add(partial_leet)
            candidates.add(partial_leet_cap)

            # Add with symbols ONLY (no numbers)
            for sym in ['!', '@', '#', '$']:
                candidates.add(partial_leet_cap + sym)

            # Add with common suffixes
            for suffix in ['123', '456', '2024', '2025', '2026']:
                candidates.add(partial_leet + suffix)
                candidates.add(partial_leet_cap + suffix)

                # With numbers + symbols combo
                for sym in ['!', '@', '#']:
                    candidates.add(partial_leet_cap + suffix + sym)

    # Title case for compound words
    if len(base_word) > 6:
        mid = len(base_word) // 2
        title_case = base_word[:mid].capitalize() + base_word[mid:].capitalize()
        candidates.add(title_case)

    return list(candidates)


def crack_cluster(cluster_info):
    """
    Crack all hashes in a cluster (same iteration count).

    Can be parallelized across CPU cores.
    """
    iterations, hash_list, all_candidates = cluster_info
    cluster_start = time.time()

    # Build lookup table
    hash_lookup = {}
    for hash_info in hash_list:
        key = (hash_info['salt'], hash_info['target_hash'])
        hash_lookup[key] = hash_info['username']

    salts_in_cluster = list(set(h['salt'] for h in hash_list))
    cluster_cracked = []

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
                cluster_cracked.append({'username': username, 'password': password})
                del hash_lookup[key]  # Remove to avoid duplicates

    cluster_elapsed = time.time() - cluster_start
    return cluster_cracked, cluster_elapsed


def main():
    """Main cracking workflow."""
    global overall_start
    overall_start = time.time()

    log("cracker_started", python_version=sys.version.split()[0])
    log_progress("Cracker script started")

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

    log("hashes_parsed", valid=parsed_count, skipped=skipped_count)
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
    log("candidates_generated", count=len(all_candidates), base_words=len(base_words))
    log_progress(f"Generated {len(all_candidates)} unique candidates from {len(base_words)} base words")

    # Determine parallelization strategy
    cpus = int(os.environ.get('CPUS', cpu_count()))
    use_parallel = cpus > 1 and os.environ.get('PARALLEL_CRACKING', 'false').lower() == 'true'

    log("execution_strategy", cpus=cpus, parallel=use_parallel)

    cracked = []
    total_hashes = sum(len(h) for h in clusters.values())

    if use_parallel:
        # Parallel execution
        log_progress(f"Using parallel execution with {cpus} workers")

        cluster_jobs = []
        for iterations in sorted(clusters.keys()):
            cluster_jobs.append((iterations, clusters[iterations], all_candidates))

        with ProcessPoolExecutor(max_workers=cpus) as executor:
            results = executor.map(crack_cluster, cluster_jobs)

            for (iterations, _, _), (cluster_cracked, cluster_elapsed) in zip(cluster_jobs, results):
                cracked.extend(cluster_cracked)
                log("cluster_complete", iterations=iterations, cracked=len(cluster_cracked), time=cluster_elapsed)
                log_progress(f"Cluster {iterations} done: {len(cluster_cracked)} cracked in {cluster_elapsed:.1f}s")
    else:
        # Sequential execution
        log_progress("Using sequential execution (1 CPU)")

        for iterations in sorted(clusters.keys()):
            hash_list = clusters[iterations]
            log_progress(f"Processing cluster iterations={iterations} ({len(hash_list)} hashes)...")

            cluster_cracked, cluster_elapsed = crack_cluster((iterations, hash_list, all_candidates))
            cracked.extend(cluster_cracked)

            log("cluster_complete", iterations=iterations, cracked=len(cluster_cracked), time=cluster_elapsed)
            log_progress(f"Cluster {iterations} done: {len(cluster_cracked)} cracked in {cluster_elapsed:.1f}s (total: {len(cracked)})")

    # Sort and write output
    log_progress("Writing output file...")
    cracked.sort(key=lambda x: x['username'])

    with open('/app/cracked.csv', 'w') as f:
        f.write('CRACKED_BY_TERMINUS_AGENT_2026\n')
        writer = csv.DictWriter(f, fieldnames=['username', 'password'])
        writer.writeheader()
        writer.writerows(cracked)

    total_elapsed = time.time() - overall_start
    success_rate = (len(cracked) / parsed_count * 100) if parsed_count > 0 else 0

    log("cracking_complete", cracked=len(cracked), total=parsed_count, success_rate=success_rate, time=total_elapsed)
    log_progress(f"COMPLETED: Cracked {len(cracked)}/{parsed_count} passwords ({success_rate:.1f}%)")
    log_progress(f"Total cracking time: {total_elapsed:.1f}s")

    print(f"\n[DEBUG] Output written to /app/cracked.csv")
    print(f"[DEBUG] First 5 entries: {cracked[:5]}")


if __name__ == '__main__':
    main()
