#!/usr/bin/env python3
"""
Validates Terminus-2 tasks against quality guidelines.
Run this before committing task changes.

Usage:
    python scripts/validate_task.py <file_or_directory>
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Define validation rules based on Terminus-2 guidelines
GUIDELINES = {
    "no_latency_tests": {
        "pattern": r"assert.*latency.*<|assert.*p\d{2}.*<|time\.time\(\).*<|timeit|perf_counter.*<",
        "message": "❌ Latency-based tests detected - hardware-dependent tests are forbidden",
        "severity": "error",
    },
    "no_oracle_conditionals": {
        "pattern": r"EVAL_IS_ORACLE|if.*oracle|if.*agent|IS_ORACLE",
        "message": "❌ Oracle/Agent conditional logic detected - tests must be identical",
        "severity": "error",
    },
    "no_web_fetching": {
        "pattern": r"urllib\.request\.urlopen\(['\"]http|requests\.get\(['\"]http|curl\s+http|wget\s+http",
        "message": "⚠️  Web URL fetching detected - consider pre-downloading data",
        "severity": "warning",
    },
    "no_reserved_dirs": {
        "pattern": r"mkdir.*[/\s](tests|oracle)(?:\s|$|/)|RUN\s+mkdir.*[/\s](tests|oracle)(?:\s|$|/)",
        "message": "❌ Creating reserved /tests or /oracle directories in Dockerfile",
        "severity": "error",
    },
    "reward_file_handling": {
        "pattern": r"exit\s+\$exit_code|exit\s+\$\?(?!.*reward\.txt)",
        "message": "⚠️  Early exit detected - ensure reward.txt is created (use trap or ensure block)",
        "severity": "warning",
    },
    "test_dir_default": {
        "pattern": r"\$\{?TEST_DIR\}?(?!.*:-)",
        "message": "⚠️  TEST_DIR used without default value - use ${TEST_DIR:-/tests}",
        "severity": "warning",
        "file_types": [".sh"],
    },
    "no_copy_tests": {
        "pattern": r"COPY\s+tests|COPY\s+\./tests|COPY\s+\.\.\/tests",
        "message": "❌ Dockerfile copying /tests directory - tests should not be in image",
        "severity": "error",
        "file_types": ["Dockerfile"],
    },
    "no_copy_oracle": {
        "pattern": r"COPY\s+oracle|COPY\s+\./oracle|COPY\s+\.\.\/oracle",
        "message": "❌ Dockerfile copying /oracle directory - oracle should not be in image",
        "severity": "error",
        "file_types": ["Dockerfile"],
    },
}

# Task.toml specific checks (now handled in validate_task_structure for better context)
TASK_TOML_GUIDELINES = {}


def validate_file(filepath: Path) -> List[Tuple[str, str, str]]:
    """
    Validate a single file against guidelines.

    Returns:
        List of (message, severity, rule_name) tuples
    """
    try:
        content = filepath.read_text()
    except Exception as e:
        return [(f"⚠️  Could not read file: {e}", "warning", "read_error")]

    issues = []

    # Check regular guidelines
    for rule_name, rule in GUIDELINES.items():
        # Check if rule applies to this file type
        if "file_types" in rule:
            if not any(str(filepath).endswith(ft) for ft in rule["file_types"]):
                continue

        if re.search(rule["pattern"], content, re.MULTILINE | re.IGNORECASE):
            issues.append((rule["message"], rule["severity"], rule_name))

    # Special handling for task.toml files
    if filepath.name == "task.toml":
        for rule_name, rule in TASK_TOML_GUIDELINES.items():
            match_found = re.search(rule["pattern"], content, re.MULTILINE)
            inverse = rule.get("inverse", False)

            # If inverse is True, we want to flag when pattern is NOT found
            if inverse and not match_found:
                issues.append((rule["message"], rule["severity"], rule_name))
            elif not inverse and match_found:
                issues.append((rule["message"], rule["severity"], rule_name))

    return issues


def validate_task_structure(task_dir: Path) -> List[Tuple[str, str, str]]:
    """
    Validate overall task structure.

    Returns:
        List of (message, severity, rule_name) tuples
    """
    issues = []

    # Check for required files
    if not (task_dir / "task.toml").exists():
        issues.append(("❌ task.toml not found", "error", "missing_task_toml"))

    if not (task_dir / "instruction.md").exists():
        issues.append(("⚠️  instruction.md not found", "warning", "missing_instruction"))

    # Check for tests directory
    tests_dir = task_dir / "tests"
    if tests_dir.exists():
        if not (tests_dir / "test.sh").exists():
            issues.append(
                ("⚠️  tests/test.sh not found", "warning", "missing_test_script")
            )

    # Check docker-compose configuration
    has_docker_compose = (
        (task_dir / "docker-compose.yml").exists()
        or (task_dir / "docker-compose.yaml").exists()
        or (task_dir / "environment" / "docker-compose.yml").exists()
        or (task_dir / "environment" / "docker-compose.yaml").exists()
    )

    if has_docker_compose and (task_dir / "task.toml").exists():
        task_toml_content = (task_dir / "task.toml").read_text()
        if "is_multi_container" not in task_toml_content:
            issues.append(
                (
                    "⚠️  docker-compose.yml found but is_multi_container flag not set in task.toml",
                    "warning",
                    "missing_multi_container_flag",
                )
            )

    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_task.py <file_or_directory>")
        print("\nValidates Terminus-2 tasks against quality guidelines.")
        sys.exit(1)

    target = Path(sys.argv[1])

    if not target.exists():
        print(f"❌ Path does not exist: {target}")
        sys.exit(1)

    # Collect files to validate
    # Exclude paths that shouldn't be validated
    exclude_patterns = ["scripts/", ".git/", "__pycache__/", ".ruff_cache/", "jobs/"]

    if target.is_file():
        files = [target]
        task_dir = None
    else:
        # Find all relevant files
        files = []
        all_files = []
        all_files.extend(target.rglob("*.py"))
        all_files.extend(target.rglob("*.sh"))
        all_files.extend(target.rglob("Dockerfile"))
        all_files.extend(target.rglob("docker-compose.yml"))
        all_files.extend(target.rglob("task.toml"))

        # Filter out excluded paths
        for file in all_files:
            rel_path = str(file.relative_to(target))
            if not any(excl in rel_path for excl in exclude_patterns):
                files.append(file)

        task_dir = target

    all_issues: Dict[str, List[Tuple[str, str, str]]] = {}

    # Validate individual files
    for file in files:
        issues = validate_file(file)
        if issues:
            all_issues[
                str(file.relative_to(target.parent if target.is_file() else target))
            ] = issues

    # Validate task structure if we're checking a directory
    if task_dir:
        structure_issues = validate_task_structure(task_dir)
        if structure_issues:
            all_issues["[Task Structure]"] = structure_issues

    # Report results
    error_count = 0
    warning_count = 0

    if all_issues:
        print("🚨 Guideline Violations Found:\n")
        for file, issues in sorted(all_issues.items()):
            print(f"📄 {file}")
            for message, severity, rule_name in issues:
                print(f"  {message} [{rule_name}]")
                if severity == "error":
                    error_count += 1
                else:
                    warning_count += 1
            print()

        print("─" * 60)
        print(f"Summary: {error_count} error(s), {warning_count} warning(s)")

        if error_count > 0:
            print("\n💡 Tip: Review guidelines at docs/task_quality_guidelines.md")
            sys.exit(1)
        else:
            print("\n⚠️  Warnings found but no blocking errors")
            sys.exit(0)
    else:
        print("✅ All files comply with Terminus-2 guidelines!")
        sys.exit(0)


if __name__ == "__main__":
    main()
