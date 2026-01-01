# Task Validation Checklist

## Pre-Submission Validation

### 1. Oracle Test (Must Pass)
```bash
cd /Users/nickmoore/snorkel-local/tasks/arm7-triage
harbor run --agent oracle --path .
```

**Expected**: ✅ PASS with reward=1

**Validates**:
- Both ARM targets build successfully
- Musl binary is statically linked
- Musl binary is under 5MB
- Glibc binary links libz.so.1
- Host binary runs correctly
- All tests pass

### 2. File Structure Check
```bash
# Required files exist
ls -la instruction.md
ls -la Cargo.toml
ls -la src/main.rs
ls -la solution/solve.sh
ls -la tests/test.sh
ls -la tests/test_outputs.py
ls -la .cargo/config.toml
```

### 3. Instruction Clarity Check
- [ ] Both targets clearly documented
- [ ] Rustflags requirements explicit
- [ ] Binary size constraint mentioned
- [ ] OpenSSL dependency noted
- [ ] Configuration file requirements clear
- [ ] Verification commands provided

### 4. Test Coverage Check
```bash
# Run pytest directly to see all test names
cd /Users/nickmoore/snorkel-local/tasks/arm7-triage
pytest tests/test_outputs.py -v
```

**Expected tests**:
- [ ] test_cli_build_and_outputs_host_release
- [ ] test_cli_usage_and_invalid_integer_errors
- [ ] test_armv7_cross_build_artifacts_exist_build_only (validates both targets)
- [ ] test_verifier_env_sh_not_modified_by_tests
- [ ] test_pkg_config_cross_configured
- [ ] test_task_uses_absolute_app_path_in_environment
- [ ] test_cargo_config_contains_required_env_vars

### 5. Difficulty Validation (Run 2-3 times each)

```bash
# GPT-5 (target: 45-55% pass rate)
harbor run -a terminus-2 -m openai/@openai-tbench/gpt-5 -p arm7-triage

# Claude Sonnet 4.5 (target: 40-50% pass rate)
harbor run -a terminus-2 -m openai/@anthropic-tbench/claude-sonnet-4-5-20250929 -p arm7-triage
```

**Expected Results**:
- Oracle: 100% (5/5 passes)
- GPT-5: 40-60% (2-3/5 passes)
- Claude: 40-60% (2-3/5 passes)

### 6. Common Failure Modes to Verify

Run a few test runs and confirm agents fail for good reasons:

**Good failures** (task difficulty):
- [ ] Agent builds only one target (misses musl or glibc)
- [ ] Agent doesn't configure rustflags correctly
- [ ] Agent's musl binary is dynamically linked
- [ ] Agent's musl binary exceeds 5MB
- [ ] Agent doesn't install perl/make for OpenSSL
- [ ] Agent's env.sh and config.toml don't match

**Bad failures** (task issues):
- [ ] Ambiguous instructions
- [ ] Environment issues
- [ ] Impossible requirements
- [ ] Time-dependent failures

### 7. Anti-Cheating Checks

The tests include canary strings that should NOT appear:
- [ ] "Terminus-EC-Training-stateful"
- [ ] "Submission Checklist"
- [ ] "harbor run --agent oracle"
- [ ] "check_canary"
- [ ] "test 1", "test 2"

### 8. Documentation Check

- [ ] DIFFICULTY_CHANGES.md explains rationale
- [ ] CHANGES_SUMMARY.md lists all modifications
- [ ] instruction.md is clear and complete
- [ ] No sensitive information in files
- [ ] No hardcoded solutions in tests

## Final Submission Criteria

- [ ] Oracle passes 100%
- [ ] Frontier models pass 40-60%
- [ ] All tests validate behavior, not implementation
- [ ] Instructions are clear but not trivial
- [ ] Task is fair (no impossible requirements)
- [ ] Difficulty is appropriate for Medium tier

## Notes

- If oracle fails: Fix the task
- If pass rate > 60%: Add more complexity
- If pass rate < 40%: Simplify or clarify instructions
- If failures are "bad": Improve documentation
