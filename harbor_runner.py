"""Harbor framework runner with LangGraph integration."""
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, Dict, List

from graph_config import HarborGraph, AgentState


class HarborRunner:
    """Runner for Harbor tasks using LangGraph."""
    
    def __init__(self, model: str = None, checkpointer=None):
        """Initialize Harbor runner.
        
        Args:
            model: Model name to use. Defaults to environment variable or default
            checkpointer: Optional checkpointer for state persistence
        """
        self.graph_builder = HarborGraph(model=model, checkpointer=checkpointer)
        self.graph = self.graph_builder.graph
    
    def run_task(
        self,
        task_name: str,
        config: Optional[Dict] = None,
        task_base_path: str = "tasks"
    ) -> Dict:
        """Run a Harbor task through LangGraph.
        
        Args:
            task_name: Name of the task (directory name in tasks/)
            config: Optional configuration dict with max_episodes, etc.
            task_base_path: Base path to tasks directory
            
        Returns:
            Dictionary with task execution results
        """
        task_path = Path(task_base_path) / task_name
        
        if not task_path.exists():
            raise ValueError(f"Task path does not exist: {task_path}")
        
        # Create job directory
        timestamp = datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
        job_dir = task_path / "jobs" / timestamp
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save config
        config_dict = config or {}
        (job_dir / "config.json").write_text(json.dumps(config_dict, indent=2))
        
        initial_state: AgentState = {
            "task_id": task_name,
            "task_path": str(task_path),
            "instruction": "",
            "environment_ready": False,
            "current_episode": 0,
            "max_episodes": config.get("max_episodes", 10) if config else 10,
            "trajectory": [],
            "files_modified": [],
            "test_results": None,
            "oracle_solution": None,
            "error": None,
            "should_continue": True,
            "container_name": None,
            "task_config": None,
            "current_run": timestamp
        }
        
        # Run graph
        thread_id = f"{task_name}-{timestamp}"
        graph_config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100  # Increase from default 25 for complex agent workflows
        }
        
        try:
            final_state = self.graph.invoke(initial_state, graph_config)
        except Exception as e:
            final_state = {
                **initial_state,
                "error": f"Graph execution failed: {str(e)}"
            }
        
        # Save results
        result = {
            "task": task_name,
            "timestamp": timestamp,
            "episodes": final_state.get("current_episode", 0),
            "success": (
                final_state.get("test_results", {}).get("passed", False)
                if final_state.get("test_results")
                else False
            ),
            "trajectory": final_state.get("trajectory", []),
            "error": final_state.get("error"),
            "test_results": final_state.get("test_results"),
            "oracle_solution": final_state.get("oracle_solution")
        }
        
        (job_dir / "result.json").write_text(json.dumps(result, indent=2))
        
        # Save full state for debugging
        (job_dir / "state.json").write_text(json.dumps(final_state, indent=2, default=str))
        
        return result
    
    def batch_run(
        self,
        tasks: List[str],
        parallel: bool = False,
        task_base_path: str = "tasks",
        config: Optional[Dict] = None
    ) -> List[Dict]:
        """Run multiple tasks.
        
        Args:
            tasks: List of task names to run
            parallel: Whether to run tasks in parallel
            task_base_path: Base path to tasks directory
            config: Optional configuration to apply to all tasks
            
        Returns:
            List of result dictionaries
        """
        if parallel:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(
                    lambda task: self.run_task(task, config, task_base_path),
                    tasks
                ))
        else:
            results = [
                self.run_task(task, config, task_base_path)
                for task in tasks
            ]
        
        return results
    
    def resume_task(
        self,
        task_name: str,
        thread_id: str,
        task_base_path: str = "tasks"
    ) -> Dict:
        """Resume a previously started task from checkpoint.
        
        Args:
            task_name: Name of the task
            thread_id: Thread ID from previous run
            task_base_path: Base path to tasks directory
            
        Returns:
            Dictionary with task execution results
        """
        task_path = Path(task_base_path) / task_name
        
        # Get state from checkpoint
        graph_config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100  # Increase from default 25 for complex agent workflows
        }
        state = self.graph.get_state(graph_config)
        
        if not state.values:
            raise ValueError(f"No checkpoint found for thread_id: {thread_id}")
        
        # Continue from checkpoint
        final_state = self.graph.invoke(None, graph_config)
        
        # Save results (similar to run_task)
        result = {
            "task": task_name,
            "thread_id": thread_id,
            "episodes": final_state.get("current_episode", 0),
            "success": (
                final_state.get("test_results", {}).get("passed", False)
                if final_state.get("test_results")
                else False
            ),
            "trajectory": final_state.get("trajectory", []),
            "error": final_state.get("error"),
            "test_results": final_state.get("test_results"),
            "oracle_solution": final_state.get("oracle_solution")
        }
        
        return result
