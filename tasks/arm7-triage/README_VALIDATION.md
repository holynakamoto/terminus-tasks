# Terminus-2 Task Quality Validation Framework

This framework helps ensure your Terminus-2 tasks comply with quality guidelines through automated validation and AI assistant integration.

## Quick Start

### 1. Validate Your Task

```bash
# Validate the current task
make validate

# Or run the script directly
python3 scripts/validate_task.py .
```

Expected output:
```
✅ All files comply with Terminus-2 guidelines!
```

### 2. Test It Out

Let's intentionally create a violation to see the validator in action:

```bash
# Create a test file with a forbidden pattern
echo 'assert latency < 100' > test_bad.py

# Run validation
python3 scripts/validate_task.py .
```

You'll see:
```
🚨 Guideline Violations Found:

📄 test_bad.py
  ❌ Latency-based tests detected - hardware-dependent tests are forbidden [no_latency_tests]

────────────────────────────────────────────────────────────
Summary: 1 error(s), 0 warning(s)

💡 Tip: Review guidelines at docs/task_quality_guidelines.md
```

Clean up:
```bash
rm test_bad.py
```

## What Gets Validated

### Error-Level Violations (Will Fail)

1. **Latency/Performance Tests**
   - Pattern: `assert.*latency.*<`, `time.time().*<`, `perf_counter.*<`
   - Example: `assert latency < 100`

2. **Oracle/Agent Conditionals**
   - Pattern: `EVAL_IS_ORACLE`, `if.*oracle`, `if.*agent`
   - Example: `if EVAL_IS_ORACLE:`

3. **Reserved Directory Creation**
   - Pattern: `mkdir.*/tests`, `RUN mkdir /oracle`
   - Example: `RUN mkdir /tests` in Dockerfile

4. **Copying Tests/Oracle to Image**
   - Pattern: `COPY tests/`, `COPY oracle/`
   - Example: `COPY ./tests /tests` in Dockerfile

### Warning-Level Violations (Won't Fail, But Should Fix)

1. **Web URL Fetching at Runtime**
   - Pattern: `urllib.request.urlopen`, `requests.get("http`, `curl http`
   - Note: Package manager installs (apt, pip) are allowed

2. **Early Exits Without Reward File**
   - Pattern: `exit $exit_code`, `exit $?`
   - Solution: Use `trap` to ensure reward.txt is created

3. **TEST_DIR Without Default**
   - Pattern: `$TEST_DIR` without `:-/tests`
   - Solution: Use `${TEST_DIR:-/tests}`

4. **Missing Multi-Container Flag**
   - When docker-compose.yml exists but `is_multi_container` not in task.toml

## Files Created

```
arm7-triage/
├── scripts/
│   ├── validate_task.py           # Main validation script
│   └── pre-commit.template        # Git hook template
├── .zed/
│   ├── settings.json              # Zed AI configuration
│   └── prompts/
│       └── terminus_guidelines.md # AI assistant guidelines
├── Makefile                       # Convenience targets
└── README_VALIDATION.md          # This file
```

## Integration Options

### Option 1: Makefile (Recommended)

```bash
# Validate current task
make validate

# Run validation + linting (if ruff/mypy installed)
make lint

# Install git pre-commit hook (if in git repo)
make install-hooks
```

### Option 2: Git Pre-Commit Hook

If this task is in a git repository:

```bash
# Install the hook
make install-hooks

# Or manually:
cp scripts/pre-commit.template .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Now validation runs automatically before every commit!

### Option 3: Zed AI Assistant

The framework includes Zed configuration to make your AI assistant aware of guidelines.

When you open this project in Zed, the AI will:
- Know the Terminus-2 guidelines
- Suggest compliant patterns
- Warn about violations before you create them

Guidelines are in: `.zed/prompts/terminus_guidelines.md`

### Option 4: Direct Script

```bash
# Validate a single file
python3 scripts/validate_task.py tests/test.sh

# Validate entire task directory
python3 scripts/validate_task.py .

# Validate multiple tasks (from parent directory)
python3 scripts/validate_task.py /path/to/tasks/task1
python3 scripts/validate_task.py /path/to/tasks/task2
```

## Validation Script Behavior

### Exit Codes

- `0`: Success (all checks passed or only warnings)
- `1`: Failure (one or more errors found)

### Severity Levels

- **Error**: Blocks the build, must be fixed
- **Warning**: Should be fixed, but won't block

### Excluded Paths

The validator automatically excludes:
- `scripts/` - validation scripts themselves
- `.git/` - git metadata
- `__pycache__/` - Python cache
- `.ruff_cache/` - Ruff cache
- `jobs/` - execution artifacts

## Example Validation Results

### Clean Task
```bash
$ make validate
🔍 Validating task...
✅ All files comply with Terminus-2 guidelines!
```

### Task with Issues
```bash
$ make validate
🔍 Validating task...
🚨 Guideline Violations Found:

📄 tests/test.sh
  ⚠️  Early exit detected - ensure reward.txt is created (use trap or ensure block) [reward_file_handling]
  ⚠️  TEST_DIR used without default value - use ${TEST_DIR:-/tests} [test_dir_default]

📄 environment/Dockerfile
  ❌ Creating reserved /tests or /oracle directories in Dockerfile [no_reserved_dirs]

────────────────────────────────────────────────────────────
Summary: 1 error(s), 2 warning(s)

💡 Tip: Review guidelines at docs/task_quality_guidelines.md
```

## Common Fixes

### Fix: Early Exit Without Reward

**Before:**
```bash
#!/bin/bash
set -euo pipefail

some_test_command || exit 1
echo 1 > /logs/verifier/reward.txt
```

**After:**
```bash
#!/bin/bash
set -euo pipefail

# Ensure reward file is created even on early exit
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

some_test_command || exit 1
echo 1 > /logs/verifier/reward.txt
```

### Fix: TEST_DIR Without Default

**Before:**
```bash
pytest $TEST_DIR/test_outputs.py
```

**After:**
```bash
pytest ${TEST_DIR:-/tests}/test_outputs.py
```

### Fix: Reserved Directory in Dockerfile

**Before:**
```dockerfile
RUN mkdir /tests
COPY ./tests /tests
```

**After:**
```dockerfile
# Don't create or copy /tests or /oracle
# These are managed by the evaluation system
```

### Fix: Latency Test

**Before:**
```python
import time
start = time.time()
result = function_call()
assert time.time() - start < 1.0  # Hardware dependent!
```

**After:**
```python
# Test functionality, not performance
result = function_call()
assert result == expected_result
```

## Customizing Validation Rules

Edit `scripts/validate_task.py` to add/modify rules:

```python
GUIDELINES = {
    "your_rule_name": {
        "pattern": r"regex_pattern",
        "message": "❌ Your error message",
        "severity": "error",  # or "warning"
        "file_types": [".py", ".sh"]  # optional: limit to specific files
    }
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Validate Task
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Validate Terminus-2 Guidelines
        run: python3 scripts/validate_task.py .
```

### GitLab CI Example

```yaml
validate:
  stage: test
  script:
    - python3 scripts/validate_task.py .
```

## Troubleshooting

### False Positives

If the validator flags valid code:

1. Check if the pattern is in a comment or string
2. Add the path to exclusion list in `validate_task.py`:
   ```python
   exclude_patterns = ["scripts/", ".git/", "your_dir/"]
   ```
3. File an issue to improve the regex pattern

### Validation Not Running

```bash
# Check script is executable
chmod +x scripts/validate_task.py

# Check Python version (requires 3.7+)
python3 --version

# Run with verbose errors
python3 -v scripts/validate_task.py .
```

## Additional Resources

- Guidelines: `.zed/prompts/terminus_guidelines.md`
- Validation script: `scripts/validate_task.py`
- Pre-commit hook: `scripts/pre-commit.template`
- Official Terminus-2 docs: [link to docs]

## Support

If you encounter issues or have suggestions:

1. Check the validation script output for specific rule names
2. Review `.zed/prompts/terminus_guidelines.md` for detailed guidelines
3. Check the pattern in `scripts/validate_task.py` for the flagged rule
4. File an issue with example code and validation output
