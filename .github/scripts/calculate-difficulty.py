#!/usr/bin/env python3
"""
Calculate difficulty rating based on evaluation results from GPT-5 and Claude Sonnet 4.5.

Difficulty Guidelines:
- Hard: 20-40% pass rate
- Medium: 40-60% pass rate
- Easy: 60-80% pass rate
- Too Easy: >= 80% pass rate (NOT accepted)
- Too Hard: < 20% pass rate (NOT accepted)
- Broken: All agents fail to start with 0 episodes (NOT accepted)

The difficulty is based on whichever model performs BETTER (higher pass rate).
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def find_result_files(jobs_dir: str) -> List[Path]:
    """Find all result.json files in the jobs directory."""
    jobs_path = Path(jobs_dir)
    if not jobs_path.exists():
        return []

    result_files = list(jobs_path.glob("**/result.json"))
    return result_files


def parse_result_file(result_path: Path) -> Dict:
    """Parse a result.json file and extract success status."""
    try:
        with open(result_path, 'r') as f:
            data = json.load(f)

        return {
            "success": data.get("success", False),
            "task": data.get("task", "unknown"),
            "timestamp": data.get("timestamp", "unknown"),
            "episodes": data.get("episodes", 0),
            "error": data.get("error")
        }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {
            "success": False,
            "task": "unknown",
            "timestamp": "unknown",
            "episodes": 0,
            "error": str(e)
        }


def calculate_pass_rate(results: List[Dict]) -> Tuple[int, int, float]:
    """Calculate pass rate from results."""
    total = len(results)
    if total == 0:
        return 0, 0, 0.0

    passed = sum(1 for r in results if r["success"])
    pass_rate = (passed / total) * 100

    return passed, total, pass_rate


def determine_difficulty(pass_rate: float, results: List[Dict] = None) -> str:
    """
    Determine difficulty rating based on pass rate.

    Returns one of: "broken", "too_hard", "hard", "medium", "easy", "too_easy"

    - Broken: All agents fail to start (0 episodes)
    - Too Hard: < 20% pass rate (NOT accepted)
    - Hard: 20-40% pass rate (accepted)
    - Medium: 40-60% pass rate (accepted)
    - Easy: 60-80% pass rate (accepted)
    - Too Easy: >= 80% pass rate (NOT accepted)
    """
    # Check if all agents failed to start (0 episodes)
    if results:
        all_zero_episodes = all(r["episodes"] == 0 for r in results)
        if all_zero_episodes:
            return "broken"

    if pass_rate >= 80:
        return "too_easy"
    elif pass_rate >= 60:
        return "easy"
    elif pass_rate >= 40:
        return "medium"
    elif pass_rate >= 20:
        return "hard"
    else:
        return "too_hard"


def format_results_for_github(
    gpt5_results: List[Dict],
    claude_results: List[Dict],
    task_name: str
) -> str:
    """Format difficulty evaluation results for GitHub Actions summary."""
    output = []

    output.append(f"## 📊 Difficulty Evaluation Results: {task_name}")
    output.append("")

    # GPT-5 Results
    gpt5_passed, gpt5_total, gpt5_rate = calculate_pass_rate(gpt5_results)
    output.append("### 🤖 GPT-5 (with Codex agent)")
    output.append(f"- **Pass Rate**: {gpt5_passed}/{gpt5_total} ({gpt5_rate:.1f}%)")
    if gpt5_results:
        output.append(f"- **Runs**: {gpt5_total}")
        for i, result in enumerate(gpt5_results, 1):
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            output.append(f"  - Run {i}: {status} (Episodes: {result['episodes']})")
    else:
        output.append("- ⚠️ No results found")
    output.append("")

    # Claude Sonnet 4.5 Results
    claude_passed, claude_total, claude_rate = calculate_pass_rate(claude_results)
    output.append("### 🤖 Claude Sonnet 4.5 (with Claude Code agent)")
    output.append(f"- **Pass Rate**: {claude_passed}/{claude_total} ({claude_rate:.1f}%)")
    if claude_results:
        output.append(f"- **Runs**: {claude_total}")
        for i, result in enumerate(claude_results, 1):
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            output.append(f"  - Run {i}: {status} (Episodes: {result['episodes']})")
    else:
        output.append("- ⚠️ No results found")
    output.append("")

    # Determine difficulty based on BETTER performing model
    best_pass_rate = max(gpt5_rate, claude_rate)

    # Combine all results to check for broken state
    all_results = gpt5_results + claude_results
    difficulty = determine_difficulty(best_pass_rate, all_results)

    output.append("### 🎯 Difficulty Rating")
    output.append(f"- **Best Pass Rate**: {best_pass_rate:.1f}% ({'GPT-5' if gpt5_rate >= claude_rate else 'Claude Sonnet 4.5'})")

    if difficulty == "broken":
        output.append(f"- **Rating**: ❌ **BROKEN** - All agents failed to start")
        output.append("")
        output.append("🚨 **CRITICAL ISSUE**: All agent runs failed with 0 episodes (agents never started).")
        output.append("")
        output.append("**This means the task is broken or has critical issues:**")
        output.append("  - Docker build failure")
        output.append("  - Environment setup error")
        output.append("  - Task configuration problem")
        output.append("  - Invalid instruction format")
        output.append("  - Missing required files")
        output.append("")
        output.append("⚠️ **ACTION REQUIRED**: Fix the task before it can be evaluated for difficulty.")
    elif difficulty == "too_hard":
        output.append(f"- **Rating**: ❌ **TOO HARD** (<20% - Task is impossibly difficult)")
        output.append("")
        output.append("🚨 **FAILED**: This task has a pass rate below 20% and is too difficult to be useful.")
        output.append("")
        output.append("**Why this is a problem:**")
        output.append("  - Tasks with <20% pass rate are likely unsolvable or too ambiguous")
        output.append("  - Even 'HARD' tasks should be solvable by capable agents 20-40% of the time")
        output.append("  - Very low pass rates indicate unclear instructions or impossible requirements")
        output.append("")
        output.append("⚠️ **ACTION REQUIRED**: Simplify the task or clarify instructions to achieve at least 20% pass rate.")
    elif difficulty == "too_easy":
        output.append(f"- **Rating**: ❌ **TOO EASY** (≥80% - Task is too simple)")
        output.append("")
        output.append("⚠️ **ACTION REQUIRED**: This task has a pass rate above 80% and will NOT be accepted.")
        output.append("")
        output.append("**Please increase the difficulty by:**")
        output.append("  - Adding more steps")
        output.append("  - Including hidden requirements")
        output.append("  - Using more niche knowledge")
        output.append("  - Creating more complex debugging scenarios")
        output.append("  - Adding more edge cases")
    elif difficulty == "hard":
        output.append(f"- **Rating**: 🔴 **HARD** (20-40%)")
        output.append("")
        output.append("✅ This task meets the HARD difficulty criteria.")
    elif difficulty == "medium":
        output.append(f"- **Rating**: 🟡 **MEDIUM** (40-60%)")
        output.append("")
        output.append("✅ This task meets the MEDIUM difficulty criteria.")
    elif difficulty == "easy":
        output.append(f"- **Rating**: 🟢 **EASY** (60-80%)")
        output.append("")
        output.append("✅ This task meets the EASY difficulty criteria.")

    output.append("")

    # Difficulty Guidelines Reference
    output.append("### 📖 Difficulty Guidelines")
    output.append("- **Hard**: 20-40% pass rate")
    output.append("- **Medium**: 40-60% pass rate")
    output.append("- **Easy**: 60-80% pass rate")
    output.append("- **Too Easy**: ≥ 80% pass rate (NOT accepted)")
    output.append("- **Too Hard**: < 20% pass rate (NOT accepted)")
    output.append("- **Broken**: All agents fail to start (0 episodes)")
    output.append("")
    output.append("_Difficulty is based on whichever model performs better._")

    return "\n".join(output)


def main():
    if len(sys.argv) < 3:
        print("Usage: calculate-difficulty.py <task_name> <jobs_dir> [gpt5_jobs_dir] [claude_jobs_dir]", file=sys.stderr)
        print("", file=sys.stderr)
        print("If only jobs_dir is provided, it will search for all result.json files.", file=sys.stderr)
        print("If separate dirs are provided, first 5 are for GPT-5, next 5 for Claude.", file=sys.stderr)
        sys.exit(1)

    task_name = sys.argv[1]
    jobs_dir = sys.argv[2]

    # Find all result files
    all_results = find_result_files(jobs_dir)

    if not all_results:
        print(f"⚠️ No result.json files found in {jobs_dir}", file=sys.stderr)
        print("")
        print(f"## ⚠️ Difficulty Evaluation: No Results Found")
        print(f"No evaluation results found for task: {task_name}")
        sys.exit(1)

    # Parse all results
    parsed_results = [parse_result_file(r) for r in all_results]

    # Sort by file modification time (more reliable than timestamp field)
    # This preserves the execution order: GPT-5 runs first, then Claude
    all_results_with_mtime = [(r, r.stat().st_mtime) for r in all_results]
    all_results_with_mtime.sort(key=lambda x: x[1])
    sorted_result_files = [r for r, _ in all_results_with_mtime]

    # Parse in the sorted order
    parsed_results = [parse_result_file(r) for r in sorted_result_files]

    # Split results based on workflow execution order
    # Workflow runs GPT-5 5 times, then Claude 5 times
    total_runs = len(parsed_results)

    if total_runs == 10:
        # Perfect case: 5 GPT-5 + 5 Claude
        gpt5_results = parsed_results[:5]
        claude_results = parsed_results[5:]
    elif total_runs >= 2:
        # Split evenly if we have at least 2 results
        split_point = total_runs // 2
        gpt5_results = parsed_results[:split_point]
        claude_results = parsed_results[split_point:]
    elif total_runs == 1:
        # Only one result - can't determine difficulty reliably
        gpt5_results = []
        claude_results = parsed_results
    else:
        gpt5_results = []
        claude_results = []

    # Format results
    formatted_output = format_results_for_github(gpt5_results, claude_results, task_name)
    print(formatted_output)

    # Check if task is invalid
    gpt5_passed, gpt5_total, gpt5_rate = calculate_pass_rate(gpt5_results)
    claude_passed, claude_total, claude_rate = calculate_pass_rate(claude_results)
    best_pass_rate = max(gpt5_rate, claude_rate)
    all_results = gpt5_results + claude_results
    difficulty = determine_difficulty(best_pass_rate, all_results)

    if difficulty in ["broken", "too_hard", "too_easy"]:
        print("", file=sys.stderr)
        if difficulty == "broken":
            print("❌ ERROR: Task is BROKEN - all agents failed to start (0 episodes)", file=sys.stderr)
        elif difficulty == "too_hard":
            print("❌ ERROR: Task is TOO HARD (pass rate < 20%)", file=sys.stderr)
        elif difficulty == "too_easy":
            print("❌ ERROR: Task is TOO EASY (pass rate >= 80%)", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
