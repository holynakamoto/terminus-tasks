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

# Capture output and exit code
ORACLE_OUTPUT=$(harbor run -a oracle -p "$TASK_PATH" 2>&1)
ORACLE_EXIT=$?

# Show output
cmd-output "$ORACLE_OUTPUT"
echo ""

# Check result
if [ $ORACLE_EXIT -eq 0 ]; then
  success "Oracle solution passed!"
  
  # Parse result if available
  RESULT_FILE=$(find "$HOME/jobs" -name "result.json" -type f | sort -r | head -1)
  if [ -f "$RESULT_FILE" ]; then
    divider
    info "Result Details"
    
    SUCCESS=$(jq -r '.success' "$RESULT_FILE" 2>/dev/null || echo "unknown")
    EPISODES=$(jq -r '.episodes' "$RESULT_FILE" 2>/dev/null || echo "unknown")
    
    box "Success: $SUCCESS
Episodes: $EPISODES
Result: $RESULT_FILE" 86
  fi
  
  divider
  task-done "Oracle validation complete!"
  exit 0
else
  error "Oracle solution failed!"
  warning "Check logs above for details"
  exit 1
fi
