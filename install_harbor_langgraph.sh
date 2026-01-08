#!/usr/bin/env bash
#
# Harbor LangGraph - Zsh Functions Installation Script
# This script installs the Harbor LangGraph zsh functions into your zsh config
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

# Determine script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FUNCTIONS_FILE="$SCRIPT_DIR/harbor_langgraph.zsh"

# Check if functions file exists
if [[ ! -f "$FUNCTIONS_FILE" ]]; then
    error "Functions file not found: $FUNCTIONS_FILE"
    exit 1
fi

# Detect zsh config file
if [[ -f "$HOME/.zshrc" ]]; then
    ZSHRC="$HOME/.zshrc"
elif [[ -f "$HOME/.zshenv" ]]; then
    ZSHRC="$HOME/.zshenv"
else
    warning "No .zshrc or .zshenv found, creating ~/.zshrc"
    ZSHRC="$HOME/.zshrc"
    touch "$ZSHRC"
fi

info "Using zsh config: $ZSHRC"

# Check if already installed
SOURCE_LINE="source \"$FUNCTIONS_FILE\""
if grep -q "harbor_langgraph.zsh" "$ZSHRC"; then
    warning "Harbor LangGraph functions already installed in $ZSHRC"
    read -p "Reinstall? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    # Remove old installation
    sed -i.bak '/harbor_langgraph.zsh/d' "$ZSHRC"
fi

# Add source line to zshrc
echo "" >> "$ZSHRC"
echo "# Harbor LangGraph Integration" >> "$ZSHRC"
echo "$SOURCE_LINE" >> "$ZSHRC"

success "Installed Harbor LangGraph functions to $ZSHRC"

# Detect Harbor root directory
echo ""
info "Detecting Harbor installation..."

# Try common locations
HARBOR_CANDIDATES=(
    "$HOME/terminus-2"
    "$HOME/harbor"
    "$HOME/projects/terminus-2"
    "$PWD"
    "$PWD/.."
)

HARBOR_ROOT=""
for candidate in "${HARBOR_CANDIDATES[@]}"; do
    if [[ -d "$candidate/tasks" ]] && [[ -f "$candidate/agent_script.py" ]]; then
        HARBOR_ROOT="$candidate"
        break
    fi
done

if [[ -n "$HARBOR_ROOT" ]]; then
    success "Found Harbor installation: $HARBOR_ROOT"
    
    # Ask if user wants to set environment variables
    read -p "Set HARBOR_ROOT environment variable? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "" >> "$ZSHRC"
        echo "# Harbor LangGraph Environment" >> "$ZSHRC"
        echo "export HARBOR_ROOT=\"$HARBOR_ROOT\"" >> "$ZSHRC"
        echo "export HARBOR_LG_DIR=\"\$HARBOR_ROOT/langgraph\"" >> "$ZSHRC"
        success "Environment variables configured"
    fi
else
    warning "Could not detect Harbor installation"
    info "You can manually set HARBOR_ROOT in your .zshrc:"
    echo "  export HARBOR_ROOT=\"/path/to/terminus-2\""
fi

# Check for LangGraph directory
echo ""
info "Checking LangGraph directory..."

if [[ -n "$HARBOR_ROOT" ]]; then
    LG_DIR="$HARBOR_ROOT/langgraph"
    if [[ ! -d "$LG_DIR" ]]; then
        read -p "Create LangGraph directory at $LG_DIR? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mkdir -p "$LG_DIR"
            success "Created $LG_DIR"
        fi
    else
        success "LangGraph directory exists: $LG_DIR"
    fi
fi

# Check dependencies
echo ""
info "Checking dependencies..."

# Check Python
if command -v python &> /dev/null || command -v python3 &> /dev/null; then
    success "Python installed"
else
    error "Python not found. Please install Python 3.8+"
fi

# Check pip
if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    success "pip installed"
else
    warning "pip not found"
fi

# Check Docker
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null 2>&1; then
        success "Docker is running"
    else
        warning "Docker is installed but not running"
    fi
else
    warning "Docker not found"
fi

# Check jq (for JSON parsing in functions)
if command -v jq &> /dev/null; then
    success "jq installed"
else
    warning "jq not found (recommended for job analysis)"
    info "Install with: brew install jq (macOS) or apt install jq (Linux)"
fi

# Installation complete
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Next steps:"
echo "  1. Reload your shell: source ~/.zshrc"
echo "  2. Test installation: hlg-test"
echo "  3. View available commands: hlg-help"
echo ""
info "Optional setup:"
echo "  • Install dependencies: hlg-setup"
echo "  • Configure API keys:"
echo "    export ANTHROPIC_API_KEY='your-key'"
echo "    export PORTKEY_API_KEY='your-key'"
echo ""
info "Quick start:"
echo "  hlg-ls                    # List available tasks"
echo "  hlg-run cracked256        # Run a task"
echo "  hlg-help                  # Show all commands"
echo ""
