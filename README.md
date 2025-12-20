# Terminus-2 Task Workspace

A collection of Terminus-2 tasks for AI agent evaluation.

## 📁 Structure

```
├── arm7-triage/                    # ✅ Ready
├── nca-supervised-clustering/       # ✅ Ready (web fetching warnings)
├── test-task/                     # ✅ Ready (web fetching warnings)
├── rust-tls/                      # ✅ Ready (web fetching warnings)
├── optimize-nccl-over-rocev2-infiniband/  # 🔄 Needs fixes
└── jobs/                          # Harbor test outputs
```

## 🚀 Quick Start

### Validate Tasks

```bash
# Validate all tasks
terminus-validator validate .

# Validate specific task
terminus-validator validate arm7-triage

# Quick check
terminus-validator quick-check .
```

### Test with Harbor

```bash
# Test oracle solution
cd arm7-triage
test-oracle

# Quality check
check-v

# Difficulty testing
test-diff . 10 4
```

## 📊 Task Status

| Task | Validation | Oracle | Quality | Status |
|------|------------|---------|---------|--------|
| arm7-triage | ✅ Pass | ✅ | ✅ | Ready |
| nca-supervised-clustering | ✅ Pass | ✅ | ✅ | Ready |
| test-task | ✅ Pass | ✅ | ✅ | Ready |
| rust-tls | ✅ Pass | ✅ | ✅ | Ready |
| optimize-nccl-over-rocev2-infiniband | ❌ Errors | - | - | Needs Fixes |

## 🔧 Development Workflow

1. **Create/Modify Task**
2. **Validate**: `terminus-validator validate .`
3. **Test Oracle**: `test-oracle`
4. **Check Quality**: `check-v`
5. **Test Difficulty**: `test-diff . 10 4`
6. **Commit**: `git add task/ && git commit -m "Update task"`

## 🛠️ Tools

- **Validator**: Terminus-2 guideline validation
- **Harbor**: AI agent testing framework
- **Ruff**: Python linting and formatting

## 📝 Notes

- No CI/CD pipeline (local validation only)
- All Harbor testing runs locally
- Uses Terminus-2 validator for quality checks
- Git tracks task versions and changes