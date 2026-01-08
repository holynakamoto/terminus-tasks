"""Node implementations for Harbor LangGraph workflow."""
import json
import subprocess
import re
from pathlib import Path
from typing import Literal
from langchain_anthropic import ChatAnthropic

# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are an AI agent working on a coding task. You have access to:
- Terminal commands (executed in a Docker container)
- File editing capabilities
- Task instructions and requirements

Your goal is to solve the task by:
1. Understanding the requirements from the instruction
2. Planning your approach
3. Executing commands and modifying files as needed
4. Testing your solution
5. Iterating until the solution works

When responding, format your commands clearly. You can use markdown code blocks to indicate commands:
```bash
command here
```

Be methodical and test your work frequently."""


class HarborNodes:
    """Node implementations for the Harbor workflow."""
    
    def __init__(self, llm: ChatAnthropic):
        """Initialize nodes with LLM."""
        self.llm = llm
    
    def parse_task_node(self, state: dict) -> dict:
        """Parse task.toml and instruction.md."""
        task_path = Path(state["task_path"])
        
        # Read instruction
        instruction_file = task_path / "instruction.md"
        if instruction_file.exists():
            instruction = instruction_file.read_text()
        else:
            instruction = ""
            state["error"] = f"instruction.md not found at {instruction_file}"
        
        # Parse task.toml for config
        task_config = {}
        task_toml = task_path / "task.toml"
        if task_toml.exists():
            try:
                import toml
                with open(task_toml, "r") as f:
                    task_config = toml.load(f)
            except ImportError:
                # Fallback to tomli if toml not available
                try:
                    import tomli
                    with open(task_toml, "rb") as f:
                        task_config = tomli.load(f)
                except ImportError:
                    # Fallback to built-in tomllib (Python 3.11+)
                    try:
                        import tomllib
                        with open(task_toml, "rb") as f:
                            task_config = tomllib.load(f)
                    except ImportError:
                        # Very basic TOML parsing for common fields
                        content = task_toml.read_text()
                        # Extract max_episodes if present
                        max_episodes_match = re.search(r'max_episodes\s*=\s*(\d+)', content)
                        if max_episodes_match:
                            task_config["max_episodes"] = int(max_episodes_match.group(1))
        
        max_episodes = task_config.get("agent", {}).get("max_episodes") or task_config.get("max_episodes", 10)
        
        return {
            **state,
            "instruction": instruction,
            "max_episodes": max_episodes,
            "current_episode": 0,
            "task_config": task_config
        }
    
    def setup_environment_node(self, state: dict) -> dict:
        """Build Docker environment."""
        task_path = Path(state["task_path"])
        dockerfile = task_path / "environment" / "Dockerfile"
        
        if not dockerfile.exists():
            return {
                **state,
                "error": f"Dockerfile not found at {dockerfile}",
                "environment_ready": False
            }
        
        container_name = f"harbor-{state['task_id']}"
        state["container_name"] = container_name
        
        try:
            # Build container
            result = subprocess.run(
                ["docker", "build", "-t", container_name, str(dockerfile.parent)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes default
                check=True
            )
            
            # Check if container is already running
            check_result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={container_name}"],
                capture_output=True,
                text=True
            )
            
            if not check_result.stdout.strip():
                # Start container if not running
                subprocess.run(
                    ["docker", "run", "-d", "--name", container_name, container_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            return {**state, "environment_ready": True}
        except subprocess.CalledProcessError as e:
            return {
                **state,
                "error": f"Environment setup failed: {e.stderr}",
                "environment_ready": False
            }
        except subprocess.TimeoutExpired:
            return {
                **state,
                "error": "Environment setup timed out",
                "environment_ready": False
            }
    
    def agent_episode_node(self, state: dict) -> dict:
        """Run one agent reasoning episode."""
        if state.get("error"):
            return state
        
        prompt = self._build_agent_prompt(state)
        
        try:
            response = self.llm.invoke([
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])
            
            # Parse commands from response
            commands = self._extract_commands(response.content)
            
            episode_data = {
                "episode": state["current_episode"] + 1,
                "prompt": prompt,
                "response": response.content,
                "commands": commands
            }
            
            return {
                **state,
                "current_episode": state["current_episode"] + 1,
                "trajectory": state.get("trajectory", []) + [episode_data]
            }
        except Exception as e:
            # Provide more detailed error information
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Check if it's a URL/connection error
            if "404" in error_msg or "Not Found" in error_msg:
                error_msg = f"API endpoint not found (404). Check base_url configuration. Original error: {error_msg}"
            elif "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = f"Authentication failed (401). Check API key and headers. Original error: {error_msg}"
            elif "403" in error_msg or "Forbidden" in error_msg:
                error_msg = f"Access forbidden (403). Check API key permissions. Original error: {error_msg}"
            
            return {
                **state,
                "error": f"Agent episode failed ({error_type}): {error_msg}"
            }
    
    def execute_commands_node(self, state: dict) -> dict:
        """Execute parsed commands in Docker container."""
        if state.get("error") or not state.get("environment_ready"):
            return state
        
        if not state.get("trajectory"):
            return state
        
        last_episode = state["trajectory"][-1]
        commands = last_episode.get("commands", [])
        container_name = state.get("container_name")
        
        if not container_name:
            return {
                **state,
                "error": "Container name not set"
            }
        
        results = []
        for cmd in commands:
            try:
                result = subprocess.run(
                    ["docker", "exec", container_name, "bash", "-c", cmd],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per command
                )
                results.append({
                    "command": cmd,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "command": cmd,
                    "stdout": "",
                    "stderr": "Command timed out",
                    "returncode": -1
                })
            except Exception as e:
                results.append({
                    "command": cmd,
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": -1
                })
        
        # Update trajectory with execution results
        state["trajectory"][-1]["execution_results"] = results
        return state
    
    def verify_solution_node(self, state: dict) -> dict:
        """Run test.sh to verify solution."""
        if state.get("error") or not state.get("environment_ready"):
            return state
        
        task_path = Path(state["task_path"])
        container_name = state.get("container_name")
        
        if not container_name:
            return {
                **state,
                "error": "Container name not set"
            }
        
        test_script = task_path / "tests" / "test.sh"
        
        try:
            # Copy test script to container if needed, or run it directly
            result = subprocess.run(
                ["docker", "exec", container_name, "bash", str(test_script)],
                capture_output=True,
                text=True,
                timeout=900  # 15 minute timeout
            )
            
            # Try to parse CTRF output
            passed = False
            try:
                # Check for CTRF JSON in common locations (inside container)
                ctrf_paths = [
                    "/logs/verifier/ctrf.json",
                    "/app/logs/verifier/ctrf.json"
                ]
                
                for ctrf_path in ctrf_paths:
                    check_result = subprocess.run(
                        ["docker", "exec", container_name, "test", "-f", ctrf_path],
                        capture_output=True,
                        text=True
                    )
                    if check_result.returncode == 0:
                        # File exists, read it
                        read_result = subprocess.run(
                            ["docker", "exec", container_name, "cat", ctrf_path],
                            capture_output=True,
                            text=True
                        )
                        if read_result.returncode == 0:
                            test_results = json.loads(read_result.stdout)
                            passed = test_results.get("summary", {}).get("passed", 0) > 0
                            break
                
                # Also check reward.txt
                if not passed:
                    reward_paths = [
                        "/logs/verifier/reward.txt",
                        "/app/logs/verifier/reward.txt"
                    ]
                    
                    for reward_path in reward_paths:
                        check_result = subprocess.run(
                            ["docker", "exec", container_name, "test", "-f", reward_path],
                            capture_output=True,
                            text=True
                        )
                        if check_result.returncode == 0:
                            read_result = subprocess.run(
                                ["docker", "exec", container_name, "cat", reward_path],
                                capture_output=True,
                                text=True
                            )
                            if read_result.returncode == 0:
                                reward = read_result.stdout.strip()
                                passed = reward == "1"
                                break
                
            except Exception:
                # Fallback to return code
                passed = result.returncode == 0
            
            return {
                **state,
                "test_results": {
                    "passed": passed,
                    "output": result.stdout,
                    "error": result.stderr,
                    "returncode": result.returncode
                }
            }
        except subprocess.TimeoutExpired:
            return {
                **state,
                "test_results": {
                    "passed": False,
                    "output": "",
                    "error": "Test execution timed out",
                    "returncode": -1
                }
            }
        except Exception as e:
            return {
                **state,
                "test_results": {
                    "passed": False,
                    "output": "",
                    "error": str(e),
                    "returncode": -1
                }
            }
    
    def oracle_check_node(self, state: dict) -> dict:
        """Run oracle solution for comparison."""
        task_path = Path(state["task_path"])
        oracle_script = task_path / "solution" / "solve.sh"
        
        if not oracle_script.exists():
            return {
                **state,
                "oracle_solution": "Oracle script not found"
            }
        
        try:
            result = subprocess.run(
                ["bash", str(oracle_script)],
                capture_output=True,
                text=True,
                timeout=900
            )
            
            return {
                **state,
                "oracle_solution": result.stdout
            }
        except Exception as e:
            return {
                **state,
                "oracle_solution": f"Oracle execution failed: {str(e)}"
            }
    
    def record_trajectory_node(self, state: dict) -> dict:
        """Save trajectory to job directory."""
        task_path = Path(state["task_path"])
        job_dir = task_path / "jobs" / state.get("current_run", "latest")
        job_dir.mkdir(parents=True, exist_ok=True)
        
        trajectory_file = job_dir / "trajectory.json"
        trajectory_file.write_text(
            json.dumps(state.get("trajectory", []), indent=2)
        )
        
        return state
    
    def should_continue_or_end(self, state: dict) -> Literal["continue", "oracle", "end"]:
        """Decision function for conditional routing."""
        # Success - run oracle for validation
        if state.get("test_results") and state["test_results"].get("passed"):
            return "oracle"
        
        # Max episodes reached - end
        if state.get("current_episode", 0) >= state.get("max_episodes", 10):
            return "end"
        
        # Error encountered - end
        if state.get("error"):
            return "end"
        
        # Otherwise continue
        return "continue"
    
    def _build_agent_prompt(self, state: dict) -> str:
        """Build prompt for agent episode."""
        instruction = state.get("instruction", "")
        current_episode = state.get("current_episode", 0)
        max_episodes = state.get("max_episodes", 10)
        trajectory = state.get("trajectory", [])
        
        prompt = f"""Task Instruction:
{instruction}

Current Episode: {current_episode + 1} / {max_episodes}
"""
        
        if trajectory:
            prompt += "\nPrevious Episodes:\n"
            for i, episode in enumerate(trajectory[-3:], 1):  # Last 3 episodes
                prompt += f"\nEpisode {episode.get('episode', i)}:\n"
                if episode.get("execution_results"):
                    for result in episode["execution_results"]:
                        prompt += f"Command: {result['command']}\n"
                        if result.get("stdout"):
                            prompt += f"Output: {result['stdout'][:500]}\n"
                        if result.get("stderr"):
                            prompt += f"Error: {result['stderr'][:500]}\n"
        
        if state.get("test_results"):
            test_results = state["test_results"]
            prompt += f"\nLast Test Results: {'PASSED' if test_results.get('passed') else 'FAILED'}\n"
            if test_results.get("error"):
                prompt += f"Error: {test_results['error'][:500]}\n"
        
        prompt += "\nWhat commands would you like to execute next to solve this task?"
        
        return prompt
    
    def _extract_commands(self, response: str) -> list[str]:
        """Extract bash commands from agent response, preserving multi-line constructs."""
        commands = []
        
        # Look for code blocks with bash - treat each block as a single command
        bash_block_pattern = r'```(?:bash|sh)?\n(.*?)```'
        matches = re.findall(bash_block_pattern, response, re.DOTALL)
        for match in matches:
            # Keep the entire code block as a single command
            # This preserves heredocs, loops, functions, etc.
            command = match.strip()
            if command:
                commands.append(command)
        
        # Also look for inline commands (lines starting with $ or standalone commands)
        # But skip if they're already in a code block
        in_code_block = False
        current_command = []
        lines = response.split('\n')
        
        for line in lines:
            # Track code block boundaries
            if '```' in line:
                in_code_block = not in_code_block
                continue
            
            # Skip lines inside code blocks (already captured above)
            if in_code_block:
                continue
            
            line = line.strip()
            if not line:
                # Empty line - if we have a command in progress, finalize it
                if current_command:
                    commands.append('\n'.join(current_command))
                    current_command = []
                continue
            
            # Look for command-like lines
            if line.startswith('$'):
                # Finalize any command in progress
                if current_command:
                    commands.append('\n'.join(current_command))
                    current_command = []
                commands.append(line[1:].strip())
            elif line.startswith('#') or line.startswith('*'):
                # Comment or markdown - finalize any command in progress
                if current_command:
                    commands.append('\n'.join(current_command))
                    current_command = []
            else:
                # Check if it looks like a command
                if any(keyword in line.lower() for keyword in ['cd ', 'ls ', 'cat ', 'grep ', 'python ', 'bash ', 'sh ', 'echo ', 'mkdir ', 'touch ', 'cp ', 'mv ', 'rm ']):
                    # Check if this is a continuation of a multi-line command
                    # (heredoc, pipe, backslash continuation, etc.)
                    if (line.endswith('\\') or 
                        line.endswith('|') or 
                        line.endswith('&&') or 
                        line.endswith('||') or
                        '<<' in line or  # Heredoc start
                        'EOF' in line or 'PY' in line or 'END' in line):  # Heredoc markers
                        current_command.append(line)
                    else:
                        # Finalize any command in progress
                        if current_command:
                            commands.append('\n'.join(current_command))
                            current_command = []
                        commands.append(line)
        
        # Finalize any remaining command
        if current_command:
            commands.append('\n'.join(current_command))
        
        return commands
