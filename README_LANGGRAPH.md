# Harbor LangGraph Integration

This directory contains a LangGraph-based implementation for running Harbor framework tasks. LangGraph provides state management, checkpointing, and workflow orchestration for AI agent evaluation.

## Architecture

The integration consists of several key components:

- **`graph_config.py`**: Defines the `AgentState` TypedDict and `HarborGraph` class that builds the LangGraph workflow
- **`nodes.py`**: Implements all the workflow nodes (parse_task, setup_environment, agent_episode, etc.)
- **`harbor_runner.py`**: High-level `HarborRunner` class for executing tasks
- **`main.py`**: CLI entry point for running tasks

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

Run a single task:
```bash
python main.py cracked256 --max-episodes 10
```

List available tasks:
```bash
python main.py list
```

Run multiple tasks in batch:
```bash
python main.py --batch cracked256 pcaptls arm7-triage --parallel
```

### Python API

```python
from harbor_runner import HarborRunner

# Initialize runner
runner = HarborRunner()

# Run single task
result = runner.run_task("cracked256", config={"max_episodes": 10})
print(f"Success: {result['success']}, Episodes: {result['episodes']}")

# Run multiple tasks
tasks = ["cracked256", "pcaptls", "arm7-triage"]
results = runner.batch_run(tasks, parallel=True)

# Analyze results
success_rate = sum(r["success"] for r in results) / len(results)
print(f"Success rate: {success_rate:.2%}")
```

## Workflow

The LangGraph workflow follows this structure:

1. **parse_task**: Reads `task.toml` and `instruction.md`
2. **setup_environment**: Builds and starts Docker container
3. **agent_episode**: LLM generates commands based on task
4. **execute_commands**: Runs commands in Docker container
5. **verify_solution**: Runs `tests/test.sh` to check solution
6. **oracle_check**: (if successful) Runs oracle solution for comparison
7. **record_trajectory**: Saves episode data to job directory

The workflow loops between steps 3-7 until:
- Tests pass (→ oracle check → end)
- Max episodes reached (→ end)
- Error encountered (→ end)

## State Management

LangGraph's checkpointing allows you to:
- Resume interrupted tasks
- Debug agent behavior at each step
- Visualize the workflow graph
- Stream agent actions in real-time

## Configuration

The runner respects environment variables for LLM configuration:
- `LLM_MODEL`: Model name (default: claude-sonnet-4-20250514)
- `PORTKEY_API_KEY` or `ANTHROPIC_API_KEY`: API key
- `ANTHROPIC_BASE_URL`: Base URL for Portkey
- `ANTHROPIC_HEADERS`: JSON string of headers for Portkey

## Output

Each task run creates a job directory at `tasks/{task_name}/jobs/{timestamp}/` containing:
- `config.json`: Configuration used for the run
- `result.json`: Summary of results
- `trajectory.json`: Full episode trajectory
- `state.json`: Complete final state (for debugging)

## Advanced Features

### Custom Checkpointing

Use a persistent checkpointer for state management:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
runner = HarborRunner(checkpointer=checkpointer)
```

### Resuming Tasks

```python
# Resume from checkpoint
result = runner.resume_task("cracked256", thread_id="cracked256-2026-01-07__10-34-16")
```

### Multi-Agent Coordination

The architecture supports adding parallel agent nodes for complex tasks:

```python
# In graph_config.py, you can add:
workflow.add_node("planning_agent", planning_node)
workflow.add_node("coding_agent", coding_node)
workflow.add_node("testing_agent", testing_node)

# Agents can work in parallel
workflow.add_edge("planning_agent", ["coding_agent", "testing_agent"])
```

## Key Benefits

1. **Persistent State**: Checkpointing means you can pause/resume long-running tasks
2. **Visualization**: Built-in graph visualization helps debug agent flow
3. **Human-in-Loop**: Easy to add breakpoints for human review between episodes
4. **Parallel Execution**: Run multiple tasks concurrently with shared state management
5. **Streaming**: Stream agent thoughts/actions in real-time
6. **Debugging**: Each node is isolated, making it easy to test individual components
