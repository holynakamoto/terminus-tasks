#!/usr/bin/env python3
"""
Calculate difficulty rating based on evaluation results from GPT-5 and Claude Sonnet 4.5.

Difficulty Guidelines:
- Hard: < 40% pass rate
- Medium: < 60% pass rate
- Easy: < 80% pass rate
- Tasks with > 80% pass rate are NOT accepted

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


def determine_difficulty(pass_rate: float) -> str:
    """
    Determine difficulty rating based on pass rate.

    - Hard: < 40%
    - Medium: < 60%
    - Easy: < 80%
    - Invalid: >= 80% (task is too easy)
    """
    if pass_rate >= 80:
        return "invalid"
    elif pass_rate >= 60:
        return "easy"
    elif pass_rate >= 40:
        return "medium"
    else:
        return "hard"


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
    difficulty = determine_difficulty(best_pass_rate)

    output.append("### 🎯 Difficulty Rating")
    output.append(f"- **Best Pass Rate**: {best_pass_rate:.1f}% ({'GPT-5' if gpt5_rate >= claude_rate else 'Claude Sonnet 4.5'})")

    if difficulty == "invalid":
        output.append(f"- **Rating**: ❌ **INVALID** (>{80}% - Task is too easy)")
        output.append("")
        output.append("⚠️ **ACTION REQUIRED**: This task has a pass rate above 80% and will NOT be accepted.")
        output.append("Please increase the difficulty by:")
        output.append("  - Adding more steps")
        output.append("  - Including hidden requirements")
        output.append("  - Using more niche knowledge")
        output.append("  - Creating more complex debugging scenarios")
        output.append("  - Adding more edge cases")
    elif difficulty == "hard":
        output.append(f"- **Rating**: 🔴 **HARD** (<40%)")
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
    output.append("- **Hard**: < 40% pass rate")
    output.append("- **Medium**: 40-60% pass rate")
    output.append("- **Easy**: 60-80% pass rate")
    output.append("- **Invalid**: ≥ 80% pass rate (NOT accepted)")
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

    # Sort by timestamp to separate GPT-5 and Claude runs
    # Assuming the first 5 runs are GPT-5 and the next 5 are Claude
    # based on the workflow order
    parsed_results.sort(key=lambda x: x["timestamp"])

    # Split results (first half GPT-5, second half Claude)
    # In the workflow, we run GPT-5 5 times, then Claude 5 times
    # So we'll try to split them evenly
    total_runs = len(parsed_results)
    split_point = total_runs // 2

    gpt5_results = parsed_results[:split_point] if total_runs > 1 else []
    claude_results = parsed_results[split_point:] if total_runs > 1 else parsed_results

    # If we have exactly 10 results, assume first 5 are GPT-5, last 5 are Claude
    if total_runs == 10:
        gpt5_results = parsed_results[:5]
        claude_results = parsed_results[5:]

    # Format results
    formatted_output = format_results_for_github(gpt5_results, claude_results, task_name)
    print(formatted_output)

    # Check if task is invalid (too easy)
    gpt5_passed, gpt5_total, gpt5_rate = calculate_pass_rate(gpt5_results)
    claude_passed, claude_total, claude_rate = calculate_pass_rate(claude_results)
    best_pass_rate = max(gpt5_rate, claude_rate)

    if best_pass_rate >= 80:
        print("", file=sys.stderr)
        print("❌ ERROR: Task difficulty is INVALID (pass rate >= 80%)", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
