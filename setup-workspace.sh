#!/bin/bash
# Setup script for snorkel-local task workspace
# This configures validation WITHOUT enabling GitHub Actions

set -e

WORKSPACE_DIR="$HOME/snorkel-local"

echo "🔧 Setting up Terminus-2 task workspace"
echo "========================================"
echo ""
echo "Workspace: $WORKSPACE_DIR"
echo ""

# Check if we're in the right place
if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "❌ Error: $WORKSPACE_DIR not found"
    echo "Run this script from ~/snorkel-local or update WORKSPACE_DIR"
    exit 1
fi

cd "$WORKSPACE_DIR"

# 1. Copy config
echo "📝 Installing validator configuration..."
if [ ! -f ".terminus-validator.yaml" ]; then
    cat > .terminus-validator.yaml << 'EOF'
# See ~/terminus-validator/.terminus-validator-harbor.yaml for full options
disabled_rules: []
severity_overrides:
  test-dir-default: error
  no-web-fetching: error

file_excludes:
  - "**/.venv/**"
  - "**/jobs/**"
  - "**/.DS_Store"
  - "**/*.zip"

custom_rules:
  - path: "rules/harbor_rules.py"
    enabled: true

enabled_rules:
  - ruff-lint

output:
  format: "text"
  color: true
  show_suggestions: true

integrations:
  pre_commit:
    enabled: false  # Set to true if you want local pre-commit validation
  ci_cd:
    enabled: false  # NO GitHub Actions
  zed:
    enabled: true
EOF
    echo "✅ Created .terminus-validator.yaml"
else
    echo "ℹ️  .terminus-validator.yaml already exists"
fi

# 2. Copy .gitignore
echo ""
echo "📝 Installing .gitignore..."
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# Harbor
jobs/
.harbor/

# Task artifacts
*.zip

# macOS
.DS_Store

# IDE
.zed/
.vscode/

# Logs
*.log

# Don't ignore config
!.terminus-validator.yaml
EOF
    echo "✅ Created .gitignore"
else
    echo "ℹ️  .gitignore already exists"
fi

# 3. Optional: Initialize git
echo ""
read -p "📦 Initialize git repository? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d ".git" ]; then
        git init
        echo "✅ Initialized git repository"
        
        # Add .gitignore first
        git add .gitignore .terminus-validator.yaml
        
        echo ""
        echo "Git initialized. Next steps:"
        echo "  1. Review files to commit: git status"
        echo "  2. Add task directories: git add arm7-triage/ nca-supervised-clustering/"
        echo "  3. Commit: git commit -m 'Initial task workspace'"
        echo "  4. Add remote: git remote add origin <your-repo-url>"
        echo "  5. Push: git push -u origin main"
    else
        echo "ℹ️  Git already initialized"
    fi
fi

# 4. Test validator
echo ""
echo "🧪 Testing validator installation..."
if command -v terminus-validator &> /dev/null; then
    echo "✅ Validator available: $(which terminus-validator)"
    
    echo ""
    echo "Testing quick validation..."
    terminus-validator quick-check . || echo "⚠️  Found some issues (expected for first run)"
else
    echo "❌ Validator not found!"
    echo "Install with:"
    echo "  cd ~/terminus-validator"
    echo "  ./setup.sh"
    exit 1
fi

# 5. Optional: Create Zed config
echo ""
read -p "🎨 Create Zed configuration? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p .zed
    cat > .zed/settings.json << 'EOF'
{
  "tasks": [
    {
      "label": "Validate Task",
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
      "label": "Test Oracle",
      "command": "test-oracle",
      "args": ["${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Check Quality",
      "command": "check-v",
      "args": ["${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Test Difficulty",
      "command": "test-diff",
      "args": ["${ZED_DIRNAME}", "10", "4"],
      "reveal": "always"
    },
    {
      "label": "Ruff Check",
      "command": "terminus-validator",
      "args": ["ruff", "check", "${ZED_DIRNAME}"],
      "reveal": "always"
    },
    {
      "label": "Ruff Format",
      "command": "terminus-validator",
      "args": ["ruff", "format", "${ZED_DIRNAME}"],
      "reveal": "always"
    }
  ]
}
EOF
    echo "✅ Created .zed/settings.json"
    echo ""
    echo "Zed tasks available via: Command Palette → Tasks: Run"
fi

echo ""
echo "========================================"
echo "✅ Setup complete!"
echo ""
echo "Your workspace is configured for:"
echo "  ✓ Local task validation"
echo "  ✓ Git version control (no CI/CD)"
echo "  ✓ Zed integration (if enabled)"
echo "  ✓ Harbor workflow integration"
echo ""
echo "Quick commands:"
echo "  terminus-validator validate .        # Check all tasks"
echo "  cd arm7-triage && terminus-validator validate .  # Check one task"
echo "  terminus-validator ruff check .      # Lint all tasks"
echo "  test-oracle                          # Your shell function (still works!)"
echo ""
echo "Git workflow (local only, no CI/CD charges):"
echo "  git add <task-directory>"
echo "  git commit -m 'Add task'"
echo "  git push"
echo ""
echo "No GitHub Actions will run!"
echo "========================================"