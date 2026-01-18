#!/bin/bash
set -e

# Local Task Testing Script
# Mimics CodeBuild environment for testing tasks locally

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARBOR_TASKS_DIR="$HOME/harbor_tasks"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $0 [OPTIONS] <task-name>

Test a Harbor task locally using oracle and nop agents.

Arguments:
    task-name       Name of the task to test (e.g., cracked256)

Options:
    -t, --type      Test type: oracle, nop, or both (default: both)
    -h, --help      Show this help message

Examples:
    $0 cracked256                    # Run both oracle and nop tests
    $0 --type oracle cracked256      # Run only oracle test
    $0 -t nop cracked256             # Run only nop test

Requirements:
    - Python 3.11+ installed
    - Docker installed and running
    - uv package manager installed (or will be auto-installed)
    - harbor and terminal-bench packages (will be auto-installed)
EOF
    exit 1
}

# Parse arguments
TEST_TYPE="both"
TASK_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            TASK_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$TASK_NAME" ]; then
    echo -e "${RED}Error: Task name is required${NC}"
    usage
fi

TASK_PATH="$SCRIPT_DIR/tasks/$TASK_NAME"
if [ ! -d "$TASK_PATH" ]; then
    echo -e "${RED}Error: Task directory not found: $TASK_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Local Task Testing for: $TASK_NAME${NC}"
echo -e "${BLUE}================================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"

    # Check/Install uv
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}Installing uv package manager...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    echo -e "${GREEN}✓ uv package manager available${NC}"

    # Install harbor if needed
    if ! python3 -c "import harbor" 2>/dev/null; then
        echo -e "${YELLOW}Installing harbor...${NC}"
        uv pip install --system harbor==0.1.25 || pip3 install harbor==0.1.25
    fi
    echo -e "${GREEN}✓ harbor installed${NC}"

    # Install terminal-bench if needed
    if ! python3 -c "import terminal_bench" 2>/dev/null; then
        echo -e "${YELLOW}Installing terminal-bench...${NC}"
        uv pip install --system terminal-bench==0.2.18 || pip3 install terminal-bench==0.2.18
    fi
    echo -e "${GREEN}✓ terminal-bench installed${NC}"

    # Check bc for tests
    if ! command -v bc &> /dev/null; then
        echo -e "${YELLOW}Warning: bc not installed. Some tests may fail.${NC}"
        echo -e "${YELLOW}Install with: sudo apt-get install bc (Ubuntu/Debian) or brew install bc (macOS)${NC}"
    fi
}

# Prepare test environment
prepare_environment() {
    echo -e "${YELLOW}Preparing test environment...${NC}"

    # Create harbor tasks directory
    mkdir -p "$HARBOR_TASKS_DIR/$TASK_NAME"

    # Copy task files
    cp -r "$TASK_PATH"/* "$HARBOR_TASKS_DIR/$TASK_NAME/"

    echo -e "${GREEN}✓ Task files copied to $HARBOR_TASKS_DIR/$TASK_NAME${NC}"
    ls -R "$HARBOR_TASKS_DIR/$TASK_NAME"
}

# Run oracle test
run_oracle_test() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}🤖 Testing with Oracle agent${NC}"
    echo -e "${BLUE}================================================${NC}"

    cd "$HARBOR_TASKS_DIR"

    if harbor test --agent oracle --trials 1 "$TASK_NAME"; then
        echo -e "${GREEN}✅ Oracle test PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ Oracle test FAILED${NC}"
        return 1
    fi
}

# Run nop test
run_nop_test() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}🤖 Testing with NOP agent${NC}"
    echo -e "${BLUE}================================================${NC}"

    cd "$HARBOR_TASKS_DIR"

    if harbor test --agent nop --trials 1 "$TASK_NAME"; then
        echo -e "${RED}❌ NOP test FAILED (agent should NOT solve task)${NC}"
        return 1
    else
        echo -e "${GREEN}✅ NOP test PASSED (correctly failed)${NC}"
        return 0
    fi
}

# Main execution
main() {
    check_prerequisites
    prepare_environment

    ORACLE_RESULT=0
    NOP_RESULT=0

    # Run tests based on type
    if [ "$TEST_TYPE" = "oracle" ] || [ "$TEST_TYPE" = "both" ]; then
        run_oracle_test || ORACLE_RESULT=$?
    fi

    if [ "$TEST_TYPE" = "nop" ] || [ "$TEST_TYPE" = "both" ]; then
        run_nop_test || NOP_RESULT=$?
    fi

    # Summary
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}Test Summary for $TASK_NAME${NC}"
    echo -e "${BLUE}================================================${NC}"

    if [ "$TEST_TYPE" = "oracle" ] || [ "$TEST_TYPE" = "both" ]; then
        if [ $ORACLE_RESULT -eq 0 ]; then
            echo -e "${GREEN}✅ Oracle: PASSED${NC}"
        else
            echo -e "${RED}❌ Oracle: FAILED${NC}"
        fi
    fi

    if [ "$TEST_TYPE" = "nop" ] || [ "$TEST_TYPE" = "both" ]; then
        if [ $NOP_RESULT -eq 0 ]; then
            echo -e "${GREEN}✅ NOP: PASSED${NC}"
        else
            echo -e "${RED}❌ NOP: FAILED${NC}"
        fi
    fi

    echo -e "\n${YELLOW}Logs and artifacts available in:${NC}"
    echo -e "  $HOME/jobs/"

    # Return non-zero if any test failed
    if [ $ORACLE_RESULT -ne 0 ] || [ $NOP_RESULT -ne 0 ]; then
        exit 1
    fi

    exit 0
}

main
