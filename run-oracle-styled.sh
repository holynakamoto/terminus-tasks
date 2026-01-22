#!/bin/zsh
# Enhanced Harbor Oracle Runner with Styled Output
# Usage: ./run-oracle-styled.sh <task_name>

source ~/.zshrc_gum_styles

TASK_NAME="${1:-cracked256}"
TASK_PATH="tasks/$TASK_NAME"

# Validate task exists
if [ ! -d "$TASK_PATH" ]; then
  error "Task not found: $TASK_NAME"
  exit 1
fi

# Header
clear
header "🔬 HARBOR ORACLE VALIDATION"
divider
info "Task: $TASK_NAME"
echo ""

# Check for required files
progress "Checking task structure"
sleep 0.5

MISSING_FILES=()
[ ! -f "$TASK_PATH/instruction.md" ] && MISSING_FILES+=("instruction.md")
[ ! -f "$TASK_PATH/task.toml" ] && MISSING_FILES+=("task.toml")
[ ! -d "$TASK_PATH/solution" ] && MISSING_FILES+=("solution/")
[ ! -d "$TASK_PATH/tests" ] && MISSING_FILES+=("tests/")

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
  error "Missing required files:"
  for file in "${MISSING_FILES[@]}"; do
    echo "  ❌ $file"
  done
  exit 1
fi

success "Task structure valid"
echo ""

# Run Oracle
divider
progress "Running Oracle solution"
echo ""

# Capture output and extract job ID
ORACLE_OUTPUT=$(harbor run -a oracle -p "$TASK_PATH" 2>&1)
ORACLE_EXIT=$?

# Try to extract job ID from harbor output
JOB_ID=$(echo "$ORACLE_OUTPUT" | grep -oE "job_[a-zA-Z0-9_-]+" | head -1)

# Show output
cmd-output "$ORACLE_OUTPUT"
echo ""

# Find the result file using job ID if available
RESULT_FILE=""
if [ -n "$JOB_ID" ]; then
  # Try job-specific path first
  RESULT_FILE=$(find "$HOME/jobs/$JOB_ID" -name "result.json" -type f 2>/dev/null | head -1)
fi

if [ -z "$RESULT_FILE" ]; then
  # Fallback: find most recent result.json
  RESULT_FILE=$(find "$HOME/jobs" -name "result.json" -type f -mtime -1 2>/dev/null | sort -r | head -1)
fi

# Check result
if [ $ORACLE_EXIT -eq 0 ] && [ -f "$RESULT_FILE" ]; then
  SUCCESS=$(jq -r '.success' "$RESULT_FILE" 2>/dev/null || echo "unknown")
  EPISODES=$(jq -r '.episodes' "$RESULT_FILE" 2>/dev/null || echo "unknown")
  
  divider
  info "Result Details"
  
  box "Success: $SUCCESS
Episodes: $EPISODES
Result: $RESULT_FILE" 86
  
  divider
  task-done "Oracle validation complete!"
  exit 0
else
  error "Oracle solution failed!"
  warning "Check logs above for details"
  exit 1
fi
