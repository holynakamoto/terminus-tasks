# Harbor LangGraph Integration - Zsh Functions & Aliases
# Fixed version for python3 detection and correct paths

# ============================================================================
# Configuration - Auto-detect Python and pip with Poetry support
# ============================================================================

# Check if Poetry is available
if [[ -f "$HARBOR_ROOT/pyproject.toml" ]] && command -v poetry &> /dev/null; then
    export HARBOR_USE_POETRY=1
    # For Poetry, we'll use poetry run python/pip in subshells
    export HARBOR_PYTHON="poetry run python"
    export HARBOR_PIP="poetry run pip"
else
    export HARBOR_USE_POETRY=0
    # Fallback to system Python
    if command -v python3 &> /dev/null; then
        export HARBOR_PYTHON="python3"
    elif command -v python &> /dev/null; then
        export HARBOR_PYTHON="python"
    fi

    if command -v pip3 &> /dev/null; then
        export HARBOR_PIP="pip3"
    elif command -v pip &> /dev/null; then
        export HARBOR_PIP="pip"
    fi
fi

# HARBOR_ROOT and HARBOR_LG_DIR should be set in .zshrc
# They point to the same directory (no /langgraph subdirectory)

# ============================================================================
# Basic Aliases
# ============================================================================

alias hlg='cd $HARBOR_ROOT'
alias hroot='cd $HARBOR_ROOT'
alias htasks='cd $HARBOR_ROOT/tasks'
alias hlg-ls='ls -1 $HARBOR_ROOT/tasks 2>/dev/null || echo "No tasks found"'

# ============================================================================
# Core Functions
# ============================================================================

hlg-run() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-run <task_name> [--max-episodes N] [--model MODEL]"
        return 1
    fi
    echo "🚀 Running task: $1"
    if command -v poetry &> /dev/null && [[ -f "$HARBOR_ROOT/pyproject.toml" ]]; then
        (cd "$HARBOR_ROOT" && poetry run python main.py "$@")
    else
        (cd "$HARBOR_ROOT" && $HARBOR_PYTHON main.py "$@")
    fi
}

hlg-batch() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: hlg-batch <task1> [task2] ... [--parallel]"
        return 1
    fi
    echo "🚀 Running batch tasks"
    if command -v poetry &> /dev/null && [[ -f "$HARBOR_ROOT/pyproject.toml" ]]; then
        (cd "$HARBOR_ROOT" && poetry run python main.py --batch "$@")
    else
        (cd "$HARBOR_ROOT" && $HARBOR_PYTHON main.py --batch "$@")
    fi
}

# ============================================================================
# Job Management
# ============================================================================

hlg-jobs() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-jobs <task_name>"
        return 1
    fi
    
    local jobs_dir="$HARBOR_ROOT/tasks/$1/jobs"
    if [[ ! -d "$jobs_dir" ]]; then
        echo "❌ No jobs found for task: $1"
        return 1
    fi
    
    echo "📁 Jobs for task: $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for job in "$jobs_dir"/*(/N); do
        [[ -z "$job" ]] && continue
        local timestamp=$(basename "$job")
        local result_file="$job/result.json"
        
        if [[ -f "$result_file" ]]; then
            if command -v jq &> /dev/null; then
                local success=$(jq -r '.success // "unknown"' "$result_file" 2>/dev/null)
                local episodes=$(jq -r '.episodes // "?"' "$result_file" 2>/dev/null)
            else
                local success="unknown"
                local episodes="?"
            fi
            local status_icon=$([[ "$success" == "true" ]] && echo "✅" || echo "❌")
            echo "$status_icon $timestamp (episodes: $episodes)"
        else
            echo "⏳ $timestamp (in progress)"
        fi
    done
}

hlg-latest() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-latest <task_name>"
        return 1
    fi
    
    local jobs_dir="$HARBOR_ROOT/tasks/$1/jobs"
    if [[ ! -d "$jobs_dir" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    local latest=$(ls -t "$jobs_dir" 2>/dev/null | head -1)
    [[ -n "$latest" ]] && echo "$jobs_dir/$latest"
}

hlg-result() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-result <task_name> [job_timestamp]"
        return 1
    fi
    
    local task=$1
    local job=${2:-$(basename $(hlg-latest "$task" 2>/dev/null) 2>/dev/null)}
    
    if [[ -z "$job" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    local result_file="$HARBOR_ROOT/tasks/$task/jobs/$job/result.json"
    if [[ ! -f "$result_file" ]]; then
        echo "❌ Result not found: $result_file"
        return 1
    fi
    
    echo "📊 Result for $task/$job:"
    if command -v jq &> /dev/null; then
        jq '.' "$result_file"
    else
        cat "$result_file"
    fi
}

hlg-trajectory() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-trajectory <task_name> [episode_num]"
        return 1
    fi
    
    local task=$1
    local episode=$2
    local job=$(basename $(hlg-latest "$task" 2>/dev/null) 2>/dev/null)
    
    if [[ -z "$job" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    local traj_file="$HARBOR_ROOT/tasks/$task/jobs/$job/trajectory.json"
    if [[ ! -f "$traj_file" ]]; then
        echo "❌ Trajectory not found"
        return 1
    fi
    
    if [[ -n "$episode" ]] && command -v jq &> /dev/null; then
        jq ".[$episode]" "$traj_file"
    elif command -v jq &> /dev/null; then
        jq '.' "$traj_file"
    else
        cat "$traj_file"
    fi
}

hlg-watch() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-watch <task_name>"
        return 1
    fi
    
    local latest=$(hlg-latest "$1" 2>/dev/null)
    if [[ -z "$latest" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    local log_file="$latest/job.log"
    if [[ ! -f "$log_file" ]]; then
        log_file=$(find "$latest" -name "trial.log" -o -name "*.log" | head -1)
    fi
    
    if [[ -z "$log_file" ]]; then
        echo "❌ No log file found"
        return 1
    fi
    
    echo "👁️  Watching: $log_file"
    tail -f "$log_file"
}

# ============================================================================
# Analysis
# ============================================================================

hlg-stats() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-stats <task_name>"
        return 1
    fi
    
    local jobs_dir="$HARBOR_ROOT/tasks/$1/jobs"
    if [[ ! -d "$jobs_dir" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    echo "📈 Statistics for task: $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local total=0 success=0 total_episodes=0
    
    for job in "$jobs_dir"/*(/N); do
        [[ -z "$job" ]] && continue
        local result_file="$job/result.json"
        if [[ -f "$result_file" ]]; then
            ((total++))
            if command -v jq &> /dev/null; then
                local job_success=$(jq -r '.success // "false"' "$result_file" 2>/dev/null)
                local episodes=$(jq -r '.episodes // 0' "$result_file" 2>/dev/null)
                [[ "$job_success" == "true" ]] && ((success++))
                ((total_episodes += episodes))
            fi
        fi
    done
    
    if [[ $total -gt 0 ]]; then
        local success_rate=$(( success * 100 / total ))
        local avg_episodes=$(( total_episodes / total ))
        echo "Total runs: $total"
        echo "Successful: $success ($success_rate%)"
        echo "Failed: $((total - success))"
        echo "Avg episodes: $avg_episodes"
    else
        echo "No completed jobs found"
    fi
}

# ============================================================================
# Environment
# ============================================================================

hlg-test() {
    echo "🧪 Testing Harbor LangGraph setup..."
    echo ""
    
    # Test Python availability
    if command -v poetry &> /dev/null && [[ -f "$HARBOR_ROOT/pyproject.toml" ]]; then
        local py_version=$(cd "$HARBOR_ROOT" && poetry run python --version 2>&1)
        if [[ $? -eq 0 ]]; then
            echo "✅ Python: $py_version (via Poetry)"
        else
            echo "❌ Python not found via Poetry"
        fi
    elif command -v $HARBOR_PYTHON &> /dev/null; then
        echo "✅ Python: $($HARBOR_PYTHON --version 2>&1)"
    else
        echo "❌ Python not found (looking for: $HARBOR_PYTHON)"
    fi
    
    # Check packages - always use Poetry if available
    local packages=("langgraph" "langchain_anthropic" "toml" "docker")
    for pkg in $packages; do
        if command -v poetry &> /dev/null && [[ -f "$HARBOR_ROOT/pyproject.toml" ]]; then
            if (cd "$HARBOR_ROOT" && poetry run python -c "import $pkg" 2>/dev/null); then
                echo "✅ $pkg installed"
            else
                echo "❌ $pkg not installed"
            fi
        else
            if (cd "$HARBOR_ROOT" && $HARBOR_PYTHON -c "import $pkg" 2>/dev/null); then
                echo "✅ $pkg installed"
            else
                echo "❌ $pkg not installed"
            fi
        fi
    done
    
    if [[ -d "$HARBOR_ROOT" ]]; then
        echo "✅ Harbor root: $HARBOR_ROOT"
    else
        echo "❌ Harbor root not found: $HARBOR_ROOT"
    fi
    
    if [[ -f "$HARBOR_LG_DIR/main.py" ]]; then
        echo "✅ main.py found"
    else
        echo "❌ main.py not found at: $HARBOR_LG_DIR/main.py"
    fi
    
    if command -v docker &> /dev/null && docker ps &> /dev/null 2>&1; then
        echo "✅ Docker is running"
    else
        echo "❌ Docker not available"
    fi
    
    if command -v jq &> /dev/null; then
        echo "✅ jq installed"
    else
        echo "⚠️  jq not found (install with: brew install jq)"
    fi
    
    if [[ -n "$PORTKEY_API_KEY" || -n "$ANTHROPIC_API_KEY" ]]; then
        echo "✅ API key configured"
    else
        echo "⚠️  No API key found"
    fi
}

hlg-setup() {
    echo "📦 Installing Harbor LangGraph dependencies..."
    
    if command -v poetry &> /dev/null && [[ -f "$HARBOR_ROOT/pyproject.toml" ]]; then
        echo "Using Poetry to install dependencies..."
        (cd "$HARBOR_ROOT" && poetry install)
        echo "✅ Setup complete! (Poetry)"
    else
        echo "Using pip to install dependencies..."
        if [[ ! -f "$HARBOR_ROOT/requirements.txt" ]]; then
            echo "Creating requirements.txt..."
            cat > "$HARBOR_ROOT/requirements.txt" << 'EOFREQ'
langgraph>=0.2.0
langchain>=0.3.0
langchain-anthropic>=0.2.0
langchain-core>=0.3.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
python-dotenv>=1.0.0
toml>=0.10.2
pydantic>=2.0.0
docker>=7.0.0
click>=8.1.0
rich>=13.0.0
jsonschema>=4.0.0
EOFREQ
        fi
        
        (cd "$HARBOR_ROOT" && $HARBOR_PIP install -r "$HARBOR_ROOT/requirements.txt")
        echo "✅ Setup complete! (pip)"
    fi
}

# ============================================================================
# Cleanup
# ============================================================================

hlg-clean() {
    if [[ -z "$1" ]]; then
        echo "Usage: hlg-clean <task_name> [keep_last_n]"
        return 1
    fi
    
    local task=$1
    local keep=${2:-5}
    local jobs_dir="$HARBOR_ROOT/tasks/$task/jobs"
    
    if [[ ! -d "$jobs_dir" ]]; then
        echo "❌ No jobs found"
        return 1
    fi
    
    local total=$(ls -1 "$jobs_dir" 2>/dev/null | wc -l | tr -d ' ')
    local to_delete=$((total - keep))
    
    if [[ $to_delete -le 0 ]]; then
        echo "ℹ️  Nothing to clean (only $total jobs)"
        return 0
    fi
    
    echo "🗑️  Cleaning $to_delete old jobs (keeping last $keep)"
    ls -t "$jobs_dir" | tail -n +$((keep + 1)) | while read job; do
        echo "  Removing: $job"
        rm -rf "$jobs_dir/$job"
    done
    echo "✅ Cleanup complete"
}

hlg-clean-docker() {
    echo "🐳 Cleaning Harbor Docker containers..."
    docker ps -a | grep "harbor-" | awk '{print $1}' | xargs docker rm -f 2>/dev/null || echo "No containers found"
    echo "✅ Done"
}

# ============================================================================
# Help
# ============================================================================

hlg-help() {
    cat << 'EOFHELP'
Harbor LangGraph - Command Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Running Tasks
  hlg-run <task> [opts]     Run a single task
  hlg-batch <tasks> [opts]  Run multiple tasks

📁 Job Management
  hlg-jobs <task>           List all jobs for task
  hlg-latest <task>         Show latest job path
  hlg-result <task> [job]   View job result
  hlg-trajectory <task> [ep] View trajectory
  hlg-watch <task>          Watch running job logs

📈 Analysis
  hlg-stats <task>          Show task statistics

🔧 Environment
  hlg-test                  Test installation
  hlg-setup                 Install dependencies

🗑️ Cleanup
  hlg-clean <task> [keep]   Clean old jobs
  hlg-clean-docker          Remove Docker containers

📍 Navigation
  hlg / hroot               cd to project root
  htasks                    cd to tasks dir
  hlg-ls                    List available tasks

Examples:
  hlg-jobs cracked256
  hlg-result cracked256
  hlg-stats cracked256
  hlg-clean cracked256 10
EOFHELP
}

echo "🌊 Harbor LangGraph functions loaded!"
echo "   Root: $HARBOR_ROOT"
echo "   Python: $HARBOR_PYTHON"
echo "Run 'hlg-help' for commands"
