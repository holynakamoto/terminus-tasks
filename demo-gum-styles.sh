#!/bin/zsh
# Gum Styles Demo - A simulated CI/CD pipeline

source ~/.zshrc_gum_styles

# Clear screen for clean demo
clear

# Header
header "🚀 TERMINUS TASKS CI/CD PIPELINE"
divider

# Step 1: Environment Setup
progress "Setting up environment"
sleep 1
success "Environment ready!"

# Step 2: Running Ruff
divider
progress "Running Ruff linter"
sleep 1.5
cmd-output "ruff check tasks/cracked256"
sleep 0.5
success "Ruff checks passed!"

# Step 3: LLMaJ Check
divider
progress "Running LLMaJ validation"
sleep 2
box "LLMaJ Results:
  ✓ No PII detected
  ✓ Instructions clear
  ✓ Task well-defined" 86
success "LLMaJ validation passed!"

# Step 4: Oracle Validation
divider
progress "Running Oracle solution"
sleep 1.5
cmd-output "harbor run -a oracle -p tasks/cracked256"
sleep 0.5
success "Oracle solution verified!"

# Step 5: Difficulty Evaluation
divider
if confirm "Run difficulty evaluation? (5 GPT-5 + 5 Claude runs)"; then
  progress "Running 10 parallel evaluations"
  sleep 2
  
  box "Difficulty Results:
  GPT-5:        3/5 passed (60%)
  Claude 4.5:   4/5 passed (80%)
  
  Best Rate:    80%
  Rating:       🟢 EASY" 212
  
  success "Difficulty evaluation complete!"
else
  warning "Difficulty evaluation skipped"
fi

# Final Summary
divider
header "📊 PIPELINE SUMMARY"

gum style \
  --foreground 212 --border-foreground 212 --border rounded \
  --padding "1 2" --margin "1" \
  "| Check              | Status     |
|--------------------+------------|
| Ruff Lint          | ✅ Passed  |
| LLMaJ Validation   | ✅ Passed  |
| Oracle Solution    | ✅ Passed  |
| Difficulty Eval    | ✅ Easy    |"

divider
task-done "All checks passed! Ready to merge! 🎉"

# Show some fun Gum features
divider
info "Try these commands yourself:"

gum style \
  --foreground 245 --italic \
  --padding "0 2" \
  "  success \"Your message\"
  error \"Your message\"
  warning \"Your message\"
  info \"Your message\"
  header \"Your Title\"
  box \"Your text\" 99
  task-done \"Celebration!\""

divider
