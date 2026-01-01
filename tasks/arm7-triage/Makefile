.PHONY: validate validate-all lint help install-hooks

help:
	@echo "Terminus-2 Task Validation Targets"
	@echo ""
	@echo "  make validate       - Validate current task"
	@echo "  make validate-all   - Validate all tasks (if in multi-task repo)"
	@echo "  make lint          - Run validation + additional linting"
	@echo "  make install-hooks - Install git pre-commit hook"
	@echo ""

validate:
	@echo "🔍 Validating task..."
	@python3 scripts/validate_task.py .

validate-all:
	@echo "🔍 Validating all tasks..."
	@find . -name "task.toml" -exec dirname {} \; | xargs -I {} python3 scripts/validate_task.py {}

lint: validate
	@echo "Running additional lints..."
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff..."; \
		ruff check .; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		echo "Running mypy..."; \
		mypy .; \
	fi

install-hooks:
	@if [ -d .git ]; then \
		echo "Installing pre-commit hook..."; \
		cp scripts/pre-commit.template .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "✅ Pre-commit hook installed!"; \
	else \
		echo "❌ Not a git repository. Skipping hook installation."; \
		exit 1; \
	fi
