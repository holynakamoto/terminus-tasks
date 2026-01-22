#!/bin/zsh
# Full Task Validation Pipeline with Styled Output
# Usage: ./validate-task.sh <task_name> [--skip-difficulty]

source ~/.zshrc_gum_styles

# Load environment variables from .envrc if it exists
if [ -f ".envrc" ]; then
  source .envrc
fi

TASK_NAME="${1:-cracked256}"
SKIP_DIFFICULTY="${2}"
TASK_PATH="tasks/$TASK_NAME"

# Validate task exists
if [ ! -d "$TASK_PATH" ]; then
  error "Task not found: $TASK_NAME"
  exit 1
fi

# Header
clear
header "🚀 TERMINUS TASKS VALIDATION PIPELINE"
divider
info "Task: $TASK_NAME"
echo ""

# Track overall status
FAILED_CHECKS=()

# ============================================
# Step 1: Task Structure Check
# ============================================
divider
progress "Checking task structure"

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
  FAILED_CHECKS+=("Structure")
else
  success "Task structure valid!"
fi
echo ""

# ============================================
# Step 2: Ruff Linting
# ============================================
divider
progress "Running Ruff linter"
echo ""

RUFF_OUTPUT=$(ruff check "$TASK_PATH" 2>&1)
RUFF_EXIT=$?

if [ $RUFF_EXIT -eq 0 ]; then
  cmd-output "✓ No issues found"
  success "Ruff checks passed!"
else
  cmd-output "$RUFF_OUTPUT"
  error "Ruff checks failed!"
  FAILED_CHECKS+=("Ruff")
fi
echo ""

# ============================================
# Step 3: LLMaJ Validation
# ============================================
divider
progress "Running LLMaJ validation"
echo ""

# Set up environment (already loaded from .envrc, but ensure they're set)
export OPENAI_API_KEY="${OPENAI_API_KEY:-$PORTKEY_API_KEY}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.portkey.ai/v1}"
export LITELLM_LOG_LEVEL=ERROR

# Create temp directory for harbor
HARBOR_TASK_DIR="$HOME/harbor_tasks/$TASK_NAME"
mkdir -p "$HARBOR_TASK_DIR"
cp -r "$TASK_PATH"/* "$HARBOR_TASK_DIR/"

# Run LLMaJ check
LLMAJ_OUTPUT=$(harbor tasks check -m openai/@openai-tbench/gpt-5 --output-path "$HOME/${TASK_NAME}_llmaj.json" "$HARBOR_TASK_DIR" 2>&1)
LLMAJ_EXIT=$?

# Check for API usage limit error
if echo "$LLMAJ_OUTPUT" | grep -q "Usage Limit.*Exceeded"; then
  warning "Portkey API usage limit exceeded"
  info "LLMaJ validation skipped - check again later or use GitHub Actions"
  echo ""
elif [ -f "$HOME/${TASK_NAME}_llmaj.json" ]; then
  # Parse results
  PASSED=$(jq -r '.passed' "$HOME/${TASK_NAME}_llmaj.json" 2>/dev/null || echo "false")
  
  if [ "$PASSED" = "true" ]; then
    box "LLMaJ Results: ✓ All checks passed" 86
    success "LLMaJ validation passed!"
  else
    cmd-output "$LLMAJ_OUTPUT"
    error "LLMaJ validation failed!"
    FAILED_CHECKS+=("LLMaJ")
  fi
else
  warning "LLMaJ output file not created"
  if echo "$LLMAJ_OUTPUT" | grep -q "Error:"; then
    cmd-output "$LLMAJ_OUTPUT"
  fi
  FAILED_CHECKS+=("LLMaJ")
fi
echo ""

# ============================================
# Step 4: Oracle Validation
# ============================================
divider
progress "Running Oracle solution"
echo ""

ORACLE_OUTPUT=$(harbor run -a oracle -p "$TASK_PATH" 2>&1)
ORACLE_EXIT=$?

# Find the most recent result file
RESULT_FILE=$(find "$HOME/jobs" -name "result.json" -type f -newer "$TASK_PATH" 2>/dev/null | sort -r | head -1)

if [ -f "$RESULT_FILE" ]; then
  SUCCESS=$(jq -r '.success' "$RESULT_FILE" 2>/dev/null || echo "false")
  EPISODES=$(jq -r '.episodes' "$RESULT_FILE" 2>/dev/null || echo "0")
  REWARD=$(jq -r '.reward' "$RESULT_FILE" 2>/dev/null || echo "0")
  
  # Check if actually successful (reward should be 1.0 for oracle)
  if [ "$SUCCESS" = "true" ] && [ "$REWARD" != "0" ] && [ "$REWARD" != "0.0" ] && [ "$REWARD" != "0.00" ]; then
    box "Oracle Result:
  Success: ✓
  Episodes: $EPISODES
  Reward: $REWARD" 86
    success "Oracle solution verified!"
  else
    cmd-output "$ORACLE_OUTPUT"
    box "Oracle Result:
  Success: $SUCCESS
  Episodes: $EPISODES
  Reward: $REWARD (Expected: 1.0)" 196
    error "Oracle solution failed! Got reward $REWARD instead of 1.0"
    FAILED_CHECKS+=("Oracle")
  fi
else
  cmd-output "$ORACLE_OUTPUT"
  if [ $ORACLE_EXIT -eq 0 ]; then
    warning "Oracle completed but no result file found"
  else
    error "Oracle execution failed!"
  fi
  FAILED_CHECKS+=("Oracle")
fi
echo ""

# ============================================
# Step 5: NOP Validation
# ============================================
divider
progress "Running NOP validation"
echo ""

NOP_OUTPUT=$(harbor run -a nop -p "$TASK_PATH" 2>&1)
NOP_EXIT=$?

if [ $NOP_EXIT -eq 0 ]; then
  success "NOP validation passed!"
else
  cmd-output "$NOP_OUTPUT"
  error "NOP validation failed!"
  FAILED_CHECKS+=("NOP")
fi
echo ""

# ============================================
# Step 6: Difficulty Evaluation (Optional)
# ============================================
if [ "$SKIP_DIFFICULTY" != "--skip-difficulty" ]; then
  divider
  if confirm "Run difficulty evaluation? (5 GPT-5 + 5 Claude runs, ~10 min)"; then
    progress "Running difficulty evaluation"
    echo ""
    
    # Arrays to track results
    GPT5_RESULTS=()
    CLAUDE_RESULTS=()
    
    # Run GPT-5 evaluations
    info "Running 5 GPT-5 evaluations..."
    for i in {1..5}; do
      progress "GPT-5 run $i/5"
      
      GPT_OUTPUT=$(harbor run -a terminus-2 -m openai/@openai-tbench/gpt-5 -p "$TASK_PATH" 2>&1)
      GPT_EXIT=$?
      
      # Find result
      RESULT_FILE=$(find "$HOME/jobs" -name "result.json" -type f | sort -r | head -1)
      if [ -f "$RESULT_FILE" ]; then
        SUCCESS=$(jq -r '.success' "$RESULT_FILE" 2>/dev/null || echo "false")
        if [ "$SUCCESS" = "true" ]; then
          GPT5_RESULTS+=("pass")
          echo "  ✓ Run $i: PASS"
        else
          GPT5_RESULTS+=("fail")
          echo "  ✗ Run $i: FAIL"
        fi
      else
        GPT5_RESULTS+=("fail")
        echo "  ✗ Run $i: FAIL (no result)"
      fi
    done
    echo ""
    
    # Run Claude evaluations
    info "Running 5 Claude Sonnet 4.5 evaluations..."
    for i in {1..5}; do
      progress "Claude run $i/5"
      
      CLAUDE_OUTPUT=$(harbor run -a terminus-2 -m openai/@anthropic-tbench/claude-sonnet-4-5-20250929 -p "$TASK_PATH" 2>&1)
      CLAUDE_EXIT=$?
      
      # Find result
      RESULT_FILE=$(find "$HOME/jobs" -name "result.json" -type f | sort -r | head -1)
      if [ -f "$RESULT_FILE" ]; then
        SUCCESS=$(jq -r '.success' "$RESULT_FILE" 2>/dev/null || echo "false")
        if [ "$SUCCESS" = "true" ]; then
          CLAUDE_RESULTS+=("pass")
          echo "  ✓ Run $i: PASS"
        else
          CLAUDE_RESULTS+=("fail")
          echo "  ✗ Run $i: FAIL"
        fi
      else
        CLAUDE_RESULTS+=("fail")
        echo "  ✗ Run $i: FAIL (no result)"
      fi
    done
    echo ""
    
    # Calculate pass rates
    GPT5_PASSED=$(echo "${GPT5_RESULTS[@]}" | grep -o "pass" | wc -l | xargs)
    CLAUDE_PASSED=$(echo "${CLAUDE_RESULTS[@]}" | grep -o "pass" | wc -l | xargs)
    
    GPT5_RATE=$((GPT5_PASSED * 100 / 5))
    CLAUDE_RATE=$((CLAUDE_PASSED * 100 / 5))
    
    BEST_RATE=$((GPT5_RATE > CLAUDE_RATE ? GPT5_RATE : CLAUDE_RATE))
    
    # Determine difficulty
    if [ $BEST_RATE -ge 80 ]; then
      DIFFICULTY="🟢 EASY"
      DIFFICULTY_STATUS="too_easy"
    elif [ $BEST_RATE -ge 60 ]; then
      DIFFICULTY="🟢 EASY"
      DIFFICULTY_STATUS="easy"
    elif [ $BEST_RATE -ge 40 ]; then
      DIFFICULTY="🟡 MEDIUM"
      DIFFICULTY_STATUS="medium"
    elif [ $BEST_RATE -ge 20 ]; then
      DIFFICULTY="🔴 HARD"
      DIFFICULTY_STATUS="hard"
    else
      DIFFICULTY="❌ TOO HARD"
      DIFFICULTY_STATUS="too_hard"
    fi
    
    # Display results
    box "Difficulty Results:
  GPT-5:        $GPT5_PASSED/5 passed ($GPT5_RATE%)
  Claude 4.5:   $CLAUDE_PASSED/5 passed ($CLAUDE_RATE%)
  
  Best Rate:    $BEST_RATE%
  Rating:       $DIFFICULTY" 212
    
    if [ "$DIFFICULTY_STATUS" = "too_easy" ] || [ "$DIFFICULTY_STATUS" = "too_hard" ]; then
      warning "Task difficulty is outside acceptable range!"
      FAILED_CHECKS+=("Difficulty")
    else
      success "Difficulty evaluation complete!"
    fi
  else
    warning "Difficulty evaluation skipped"
  fi
  echo ""
fi

# ============================================
# Final Summary
# ============================================
divider
header "📊 VALIDATION SUMMARY"
echo ""

# Build summary table
SUMMARY="| Check              | Status     |\n"
SUMMARY+="|--------------------+------------|\n"

if [[ ! " ${FAILED_CHECKS[@]} " =~ " Structure " ]]; then
  SUMMARY+="| Task Structure     | ✅ Passed  |\n"
else
  SUMMARY+="| Task Structure     | ❌ Failed  |\n"
fi

if [[ ! " ${FAILED_CHECKS[@]} " =~ " Ruff " ]]; then
  SUMMARY+="| Ruff Lint          | ✅ Passed  |\n"
else
  SUMMARY+="| Ruff Lint          | ❌ Failed  |\n"
fi

if [[ ! " ${FAILED_CHECKS[@]} " =~ " LLMaJ " ]]; then
  SUMMARY+="| LLMaJ Validation   | ✅ Passed  |\n"
else
  SUMMARY+="| LLMaJ Validation   | ❌ Failed  |\n"
fi

if [[ ! " ${FAILED_CHECKS[@]} " =~ " Oracle " ]]; then
  SUMMARY+="| Oracle Solution    | ✅ Passed  |\n"
else
  SUMMARY+="| Oracle Solution    | ❌ Failed  |\n"
fi

if [[ ! " ${FAILED_CHECKS[@]} " =~ " NOP " ]]; then
  SUMMARY+="| NOP Validation     | ✅ Passed  |\n"
else
  SUMMARY+="| NOP Validation     | ❌ Failed  |\n"
fi

box "$SUMMARY" 212
echo ""

# Final result
divider
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
  task-done "All checks passed! Ready to merge! 🎉"
  exit 0
else
  error "Validation failed: ${FAILED_CHECKS[*]}"
  warning "Fix the issues above and try again"
  exit 1
fi
