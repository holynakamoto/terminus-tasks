# Setup Guide for Your Terminus-2 Workspace

## Your Current Structure

```
~/snorkel-local/                          # Your task workspace
├── arm7-triage/                          # Individual tasks
├── nca-supervised-clustering/
├── optimize-nccl-over-rocev2-infiniband/
├── rust-tls/
├── test-task/
├── .venv/                                # Your Python venv
└── jobs/                                 # Harbor test outputs

~/terminus-validator/                     # Validator (separate directory)
├── validator.py
├── cli.py
└── ...
```

## Recommended Setup (No CI/CD Charges)

### Step 1: Install Validator (One-Time)

```bash
# Install validator globally
cd ~/terminus-validator
./setup.sh

# Verify installation
which terminus-validator
# Should output: /opt/homebrew/bin/terminus-validator (or similar)
```

### Step 2: Configure Your Workspace

```bash
# Go to your workspace
cd ~/snorkel-local

# Copy the config file
cp ~/terminus-validator/.terminus-validator-harbor.yaml .terminus-validator.yaml

# Edit to disable CI/CD
nano .terminus-validator.yaml
```

**Important changes:**
```yaml
integrations:
  pre_commit:
    enabled: false  # Optional - set to true if you want local pre-commit hooks
  
  ci_cd:
    enabled: false  # NO GitHub Actions = NO CHARGES
```

### Step 3: Add .gitignore

```bash
cd ~/snorkel-local

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
.ruff_cache/

# Harbor
jobs/
.harbor/

# macOS
.DS_Store

# Task artifacts
*.zip

# Don't ignore config
!.terminus-validator.yaml
EOF
```

### Step 4: Initialize Git (Optional)

```bash
cd ~/snorkel-local

# Initialize git
git init

# Add config files first
git add .gitignore .terminus-validator.yaml

# Add your tasks (one at a time or all at once)
git add arm7-triage/
git add nca-supervised-clustering/
# ... etc

# Commit
git commit -m "Initial Terminus-2 task workspace"

# Add GitHub remote (if you want)
git remote add origin git@github.com:yourusername/terminus-tasks.git

# Push
git push -u origin main
```

## Daily Workflow

### Development (Use Your Shell Functions)

```bash
cd ~/snorkel-local/arm7-triage

# Your existing workflow - KEEP USING THESE!
test-oracle                    # Test oracle solution
check-v                        # Quality check
test-diff . 10 4              # Full difficulty test
ruff check .                  # Lint
ruff format .                 # Format

# Add: Quick structure validation
terminus-validator validate .  # Check Terminus-2 guidelines
```

### Before Committing

```bash
# Validate everything
cd ~/snorkel-local
terminus-validator validate . --fail-on-warnings

# Or validate specific task
cd arm7-triage
terminus-validator validate .

# Lint
terminus-validator ruff check .

# Commit (no CI/CD will run)
git add .
git commit -m "Update task"
git push
```

### Validating All Tasks

```bash
# From workspace root
cd ~/snorkel-local

# Quick check all tasks
terminus-validator quick-check .

# Full validation
terminus-validator validate .

# Lint all tasks
terminus-validator ruff check .

# List what rules are active
terminus-validator list-rules
```

## Zed Integration

Create `.zed/settings.json` in `~/snorkel-local`:

```json
{
  "tasks": [
    {
      "label": "Validate Current Task",
      "command": "terminus-validator",
      "args": ["validate", "${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Validate All Tasks",
      "command": "terminus-validator",
      "args": ["validate", "."],
      "reveal": "always"
    },
    {
      "label": "Test Oracle (Shell)",
      "command": "test-oracle",
      "args": ["${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Check Quality (Shell)",
      "command": "check-v",
      "args": ["${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Ruff Check & Fix",
      "command": "terminus-validator",
      "args": ["ruff", "check", "${ZED_DIRNAME}", "--fix"],
      "reveal": "always"
    }
  ]
}
```

Access via: **Command Palette** (Cmd+Shift+P) → **Tasks: Run**

## Optional: Pre-commit Validation (Local Only)

If you want automatic validation before commits (runs locally, no CI/CD):

```bash
cd ~/snorkel-local

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

echo "🔍 Running pre-commit validation (local only)..."

# Fast checks
terminus-validator validate . || exit 1
terminus-validator ruff check . || exit 1

echo "✅ Validation passed!"
EOF

chmod +x .git/hooks/pre-commit

# Update config
nano .terminus-validator.yaml
# Set: pre_commit.enabled = true
```

This runs **locally only** - no GitHub charges!

## What Gets Committed to GitHub

**✅ Should commit:**
- Task directories (`arm7-triage/`, etc.)
- `.terminus-validator.yaml` (config)
- `.gitignore`
- `README.md` (if you create one)

**❌ Should NOT commit:**
- `.venv/` (in .gitignore)
- `jobs/` (Harbor test outputs - in .gitignore)
- `*.zip` (task archives - in .gitignore)
- `.DS_Store` (macOS files - in .gitignore)
- `.ruff_cache/` (in .gitignore)

## GitHub Repository Structure

After pushing to GitHub, your repo will look like:

```
https://github.com/yourusername/terminus-tasks/
├── arm7-triage/
│   ├── task.toml
│   ├── Dockerfile
│   ├── test.sh
│   └── solution/
├── nca-supervised-clustering/
│   └── ...
├── optimize-nccl-over-rocev2-infiniband/
│   └── ...
├── .terminus-validator.yaml
├── .gitignore
└── README.md (optional)
```

**No `.github/workflows/` directory = No CI/CD = No charges!**

## Validation Without CI/CD

### Local Validation Only

```bash
# Validate before pushing
terminus-validator validate . --fail-on-warnings
terminus-validator ruff check .

# Push (no CI/CD runs)
git push
```

### Manual Task Testing

```bash
# Use your shell functions for testing
test-oracle
check-v
test-diff . 10 4

# No automated CI/CD needed!
```

## If You Later Want CI/CD (Optional)

If you decide to enable CI/CD later, you can:

1. **GitHub Actions (Free tier limits):**
   - 2,000 minutes/month for free
   - Private repos: 500 minutes/month
   - Only runs on push/PR

2. **Enable by creating:** `.github/workflows/validate.yml`

3. **Keep costs low:**
   - Only validate changed tasks
   - Skip expensive tests in CI
   - Use validator's `--fail-on-warnings` flag

But for now, **no CI/CD = no worries!**

## Summary

### Your Setup

1. **Validator installed globally:** `~/terminus-validator/`
2. **Task workspace:** `~/snorkel-local/`
3. **Config:** `~/snorkel-local/.terminus-validator.yaml`
4. **Git:** Version control only (no CI/CD)

### Your Workflow

1. **Development:** Shell functions (`test-oracle`, `check-v`, etc.)
2. **Validation:** `terminus-validator validate .`
3. **Before commit:** Quick validation
4. **Push to GitHub:** No CI/CD runs (no charges!)

### Commands Quick Reference

```bash
# Validate current task
terminus-validator validate .

# Validate all tasks
cd ~/snorkel-local && terminus-validator validate .

# Lint
terminus-validator ruff check .
terminus-validator ruff check . --fix

# Your shell functions (still work!)
test-oracle
check-v
test-diff . 10 4

# Git workflow
git add task-directory/
git commit -m "message"
git push  # No CI/CD runs!
```

## Need Help?

- Full docs: `~/terminus-validator/README.md`
- Harbor integration: `~/terminus-validator/HARBOR_INTEGRATION.md`
- Quick reference: `~/terminus-validator/QUICKREF_HARBOR.md`

**Bottom line:** Validator adds structure validation to your workflow without changing what works!