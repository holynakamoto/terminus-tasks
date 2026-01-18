# CI/CD Guide for Terminus Tasks

This repository uses a multi-tier testing strategy to validate Harbor tasks before deployment.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Testing Pipeline                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Local Testing  →  GitHub Actions  →  AWS CodeBuild    │
│    (dev fast)        (PR checks)       (production)     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Testing Levels

1. **Local Testing** (fastest - seconds to minutes)
   - Run on developer machine
   - Quick feedback loop
   - Uses local Docker

2. **GitHub Actions** (fast - minutes)
   - Automated on PR creation
   - Matrix testing across tasks
   - Parallel execution

3. **AWS CodeBuild** (production - minutes to hours)
   - Final validation
   - Multiple agent types (Oracle, NOP, Terminus-GPT, Terminus-Claude)
   - Production environment matching

## Quick Start

### Local Testing

Test a task locally before pushing:

```bash
# Test with both oracle and nop agents
./test-task-local.sh cracked256

# Test with only oracle agent
./test-task-local.sh --type oracle cracked256

# Test with only nop agent
./test-task-local.sh -t nop cracked256
```

**Prerequisites:**
- Python 3.11+
- Docker Desktop running
- 8GB+ RAM recommended

The script will auto-install:
- `uv` package manager
- `harbor` testing framework
- `terminal-bench` for result parsing

### GitHub Actions (Automatic)

When you create a PR or push to a `claude/**` branch:

1. **Changed tasks detected automatically**
   - Only tests tasks that changed
   - Compares against base branch

2. **Matrix testing runs in parallel**
   - Oracle validation (should pass)
   - NOP validation (should fail - proves task is solvable)

3. **Results appear as PR checks**
   - ✅ All checks pass = ready to merge
   - ❌ Any check fails = needs fixes

**View results:**
- Check the "Actions" tab on GitHub
- PR will show status checks
- Download artifacts for detailed logs

### AWS CodeBuild (Production)

Production testing happens automatically via CodeBuild:

```yaml
# buildspec.yml defines the production pipeline
phases:
  install:
    runtime-versions:
      python: 3.13

  pre_build:
    - Install uv, harbor, terminal-bench
    - Install system dependencies (bc)

  build:
    - Copy task files
    - Run agent tests (oracle/nop/terminus)
    - Upload results to S3
```

**Test Types:**
- `oracle` - Reference solution (should pass)
- `nop` - No-operation agent (should fail)
- `terminus_gpt` - GPT-5 agent
- `terminus_claude` - Claude Sonnet 4.5 agent
- `consolidate` - Aggregate results

## File Structure

```
terminus-tasks/
├── buildspec.yml              # AWS CodeBuild configuration
├── test-task-local.sh         # Local testing script
├── .github/workflows/
│   ├── task-validation.yml    # Task testing pipeline
│   ├── claude.yml             # Claude bot integration
│   └── claude-code-review.yml # Code review workflow
└── tasks/
    └── cracked256/            # Example task
        ├── environment/       # Docker setup
        │   └── Dockerfile
        ├── solution/          # Oracle solution
        │   └── solve.sh
        ├── tests/             # Test suite
        │   ├── test.sh
        │   └── test_outputs.py
        ├── instruction.md     # Task description
        └── task.toml          # Task metadata
```

## Buildspec.yml Configuration

The `buildspec.yml` matches the production CodeBuild environment:

### Environment Variables

Required for CodeBuild:

```bash
TEST_TYPE           # oracle | nop | terminus_gpt | terminus_claude | consolidate
RUN_NUM             # Run number for terminus tests
DOCKER_USERNAME     # Docker Hub username
DOCKER_TOKEN        # Docker Hub token (secret)
OUTPUT_S3_URI       # S3 URI for output artifacts
CODEBUILD_SRC_DIR_helper  # Path to helper scripts
```

### Phase Breakdown

**Install Phase:**
- Sets Python 3.13 runtime
- Auto-configured by CodeBuild

**Pre-Build Phase:**
```bash
1. Install uv package manager
2. Install harbor (task orchestration)
3. Install terminal-bench (result parsing)
4. Install system tools (bc for calculations)
```

**Build Phase:**
```bash
1. Copy task files to ~/harbor_tasks/
2. Docker login
3. Initialize S3 output
4. Run agent-specific tests based on TEST_TYPE
5. Upload artifacts
```

**Post-Build Phase:**
- Summary output
- Artifact collection

## GitHub Actions Workflow

### Trigger Conditions

The `task-validation.yml` workflow runs when:

1. **Pull Request** - any PR that modifies `tasks/**`
2. **Push to claude/** branches - auto-testing for bot changes
3. **Manual Dispatch** - run on-demand from Actions tab

### Workflow Jobs

#### 1. detect-changed-tasks
- Compares against base branch
- Outputs list of changed task directories
- Skips workflow if no tasks changed

#### 2. validate-oracle
- Matrix strategy across changed tasks
- Tests each task with oracle agent
- Oracle solution MUST pass
- Uploads artifacts on failure

#### 3. validate-nop
- Matrix strategy across changed tasks
- Tests each task with nop agent
- NOP agent MUST fail (proves solvability)
- Uploads artifacts on failure

#### 4. summary
- Aggregates results
- Posts to GitHub Step Summary
- Shows pass/fail status

### Secrets Required

Add these to GitHub repository secrets:

```
DOCKER_USERNAME     # Optional - for private registries
DOCKER_TOKEN        # Optional - for private registries
```

## Troubleshooting

### Local Testing Issues

**"Docker daemon is not running"**
```bash
# Start Docker Desktop
# Or on Linux:
sudo systemctl start docker
```

**"harbor not found"**
```bash
# Install manually:
pip3 install harbor==0.1.25 terminal-bench==0.2.18
```

**"Permission denied: ./test-task-local.sh"**
```bash
chmod +x test-task-local.sh
```

### GitHub Actions Issues

**"No tasks detected"**
- Make sure changes are in `tasks/` directory
- Check that files are committed

**"Oracle test failed"**
- Run locally first: `./test-task-local.sh <task-name>`
- Check logs in Actions artifacts
- Verify solution/solve.sh is correct

**"NOP test passed (should fail)"**
- Task is too easy or has leaked solution
- NOP agent shouldn't solve the task
- Review task difficulty

### CodeBuild Issues

**From logs: "Expected exactly 60 valid PBKDF2 entries, found 61"**
- Oracle data generation is creating extra entries
- Check solution/solve.sh for off-by-one errors
- Validate malformed entry generation

**"Phase FAILED: COMMAND_EXECUTION_ERROR"**
- Check buildspec.yml syntax
- Verify environment variables are set
- Review CloudWatch logs in AWS Console

**"No matching auto-discover report paths found"**
- This is normal - only warns if no artifacts
- Add explicit artifact paths if needed

## Best Practices

### Before Creating a PR

1. **Test locally first**
   ```bash
   ./test-task-local.sh <task-name>
   ```

2. **Check both agents**
   - Oracle should pass (proves solution works)
   - NOP should fail (proves task difficulty)

3. **Review test output**
   - Check `~/jobs/` directory for detailed logs
   - Verify expected vs actual behavior

### Task Development Workflow

```bash
# 1. Create/modify task
vim tasks/mytask/solution/solve.sh

# 2. Test locally (fast iteration)
./test-task-local.sh mytask

# 3. Fix issues, repeat until passing
# ...

# 4. Commit and push
git add tasks/mytask/
git commit -m "Add mytask solution"
git push

# 5. Create PR
# GitHub Actions will automatically validate

# 6. Review PR checks
# Wait for ✅ before merging

# 7. Merge triggers CodeBuild
# Production validation runs automatically
```

### Writing Good Tasks

**Oracle Solution Requirements:**
- Must be deterministic
- Should generate exactly the expected test data
- Use absolute paths (/app/*)
- Handle malformed input gracefully
- Complete within timeout (15 minutes typical)

**Test Requirements:**
- Validate file integrity (anti-cheating)
- Check output format strictly
- Verify algorithmic approach (not just output)
- Test edge cases and malformed input

**Documentation:**
- Clear instruction.md with examples
- Specify exact output format
- List all requirements and constraints
- Include example input/output

## Monitoring & Metrics

### Local Metrics
```bash
# Test execution time
time ./test-task-local.sh cracked256

# Resource usage
docker stats
```

### GitHub Actions Metrics
- View in Actions tab → Workflow runs
- Check "Timing" for job duration
- Download artifacts for detailed logs

### CodeBuild Metrics
- CloudWatch Logs for detailed output
- Build time and phase duration
- S3 artifacts for results

## Advanced Configuration

### Custom Test Types

Add new test types to buildspec.yml:

```yaml
build:
  commands:
    - |
      if [ "$TEST_TYPE" = "my_custom_test" ]; then
        python $CODEBUILD_SRC_DIR_helper/my_test.py "$TASK"
      fi
```

### Matrix Testing in GitHub Actions

Test multiple configurations:

```yaml
strategy:
  matrix:
    task: ${{ fromJson(needs.detect-changed-tasks.outputs.tasks) }}
    agent: [oracle, nop]
    python-version: ['3.11', '3.12', '3.13']
```

### Caching Dependencies

Speed up builds with caching:

```yaml
- name: Cache Python packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

## Support

**Issues with CI/CD setup:**
1. Check this guide first
2. Review workflow logs in Actions tab
3. Run locally to reproduce: `./test-task-local.sh`
4. Open GitHub issue with:
   - Task name
   - Error message
   - Local test results
   - CI/CD logs (if applicable)

**Task validation failures:**
1. Run local test with verbose output
2. Check `~/jobs/` directory for logs
3. Review test expectations vs actual output
4. Verify oracle solution is correct
