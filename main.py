"""Main entry point for Harbor LangGraph runner."""
import argparse
import sys
from pathlib import Path
from harbor_runner import HarborRunner


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run Harbor tasks using LangGraph"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task name to run (or 'list' to show available tasks)"
    )
    parser.add_argument(
        "--tasks-dir",
        default="tasks",
        help="Base directory for tasks (default: tasks)"
    )
    parser.add_argument(
        "--max-episodes",
        type=int,
        default=10,
        help="Maximum number of episodes (default: 10)"
    )
    parser.add_argument(
        "--model",
        help="Model name to use (overrides environment variable)"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Run multiple tasks in batch"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run batch tasks in parallel"
    )
    parser.add_argument(
        "--resume",
        help="Resume a task from checkpoint using thread_id"
    )
    parser.add_argument(
        "--thread-id",
        help="Thread ID for resuming (used with --resume)"
    )
    
    args = parser.parse_args()
    
    # List tasks if requested
    if args.task == "list" or (not args.task and not args.batch and not args.resume):
        tasks_dir = Path(args.tasks_dir)
        if tasks_dir.exists():
            tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir() and (d / "task.toml").exists()]
            print("Available tasks:")
            for task in sorted(tasks):
                print(f"  - {task}")
        else:
            print(f"Tasks directory not found: {tasks_dir}")
        return
    
    # Initialize runner
    runner = HarborRunner(model=args.model)
    
    # Resume task if requested
    if args.resume:
        if not args.thread_id:
            print("Error: --thread-id required when using --resume")
            sys.exit(1)
        result = runner.resume_task(args.resume, args.thread_id, args.tasks_dir)
        print(f"Resumed task: {result['task']}")
        print(f"Success: {result['success']}, Episodes: {result['episodes']}")
        return
    
    # Prepare config
    config = {
        "max_episodes": args.max_episodes
    }
    
    # Run batch if requested
    if args.batch:
        results = runner.batch_run(
            args.batch,
            parallel=args.parallel,
            task_base_path=args.tasks_dir,
            config=config
        )
        
        # Print summary
        print("\nBatch Results:")
        print("=" * 60)
        for result in results:
            status = "✓" if result["success"] else "✗"
            print(f"{status} {result['task']}: "
                  f"Success={result['success']}, "
                  f"Episodes={result['episodes']}")
            if result.get("error"):
                print(f"    Error: {result['error']}")
        
        # Calculate success rate
        success_rate = sum(r["success"] for r in results) / len(results) if results else 0
        print(f"\nSuccess rate: {success_rate:.2%} ({sum(r['success'] for r in results)}/{len(results)})")
        
        return
    
    # Run single task
    if not args.task:
        print("Error: Task name required")
        parser.print_help()
        sys.exit(1)
    
    print(f"Running task: {args.task}")
    print(f"Max episodes: {args.max_episodes}")
    print("-" * 60)
    
    try:
        result = runner.run_task(args.task, config, args.tasks_dir)
        
        print(f"\nTask completed: {result['task']}")
        print(f"Success: {result['success']}")
        print(f"Episodes: {result['episodes']}")
        
        if result.get("error"):
            print(f"Error: {result['error']}")
        
        if result.get("test_results"):
            tr = result["test_results"]
            print(f"Test passed: {tr.get('passed', False)}")
            if tr.get("error"):
                print(f"Test error: {tr['error']}")
        
        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)
        
    except Exception as e:
        print(f"Error running task: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
