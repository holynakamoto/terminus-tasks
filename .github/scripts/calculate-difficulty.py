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
import argparse
from pathlib import Path
from typing import List, Dict, Tuple


def find_result_files(jobs_dir: Path) -> List[Path]:
    """Find all result.json files in the jobs directory."""
    if not jobs_dir.exists():
        return []

    result_files = list(jobs_dir.glob("**/result.json"))
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
    """
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

    # Check if either model is completely broken (all agents failed to start)
    gpt5_broken = gpt5_results and all(r["episodes"] == 0 for r in gpt5_results)
    claude_broken = claude_results and all(r["episodes"] == 0 for r in claude_results)

    # Determine difficulty based on BETTER performing model
    best_pass_rate = max(gpt5_rate, claude_rate)

    # Check for broken state first
    if gpt5_broken or claude_broken:
        difficulty = "broken"
    else:
        difficulty = determine_difficulty(best_pass_rate, None)

    output.append("### 🎯 Difficulty Rating")
    output.append(f"- **Best Pass Rate**: {best_pass_rate:.1f}% ({'GPT-5' if gpt5_rate >= claude_rate else 'Claude Sonnet 4.5'})")

    if difficulty == "broken":
        broken_models = []
        if gpt5_broken: broken_models.append("GPT-5")
        if claude_broken: broken_models.append("Claude Sonnet 4.5")
        broken_str = " and ".join(broken_models)

        output.append(f"- **Rating**: ❌ **BROKEN** - {broken_str} agents failed to start")
        output.append("")
        output.append(f"🚨 **CRITICAL ISSUE**: All {broken_str} agent runs failed with 0 episodes.")
    elif difficulty == "too_hard":
        output.append(f"- **Rating**: ❌ **TOO HARD** (<20% - Task is impossibly difficult)")
    elif difficulty == "too_easy":
        output.append(f"- **Rating**: ❌ **TOO EASY** (≥80% - Task is too simple)")
    elif difficulty == "hard":
        output.append(f"- **Rating**: 🔴 **HARD** (20-40%)")
    elif difficulty == "medium":
        output.append(f"- **Rating**: 🟡 **MEDIUM** (40-60%)")
    elif difficulty == "easy":
        output.append(f"- **Rating**: 🟢 **EASY** (60-80%)")

    output.append("")
    output.append("### 📖 Difficulty Guidelines")
    output.append("- **Hard**: 20-40% pass rate")
    output.append("- **Medium**: 40-60% pass rate")
    output.append("- **Easy**: 60-80% pass rate")
    output.append("- **Too Easy**: ≥ 80% pass rate (NOT accepted)")
    output.append("- **Too Hard**: < 20% pass rate (NOT accepted)")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Calculate task difficulty rating.")
    parser.add_argument("task_name", help="Name of the task")
    parser.add_argument("--gpt-dir", help="Directory containing GPT-5 results")
    parser.add_argument("--claude-dir", help="Directory containing Claude results")
    parser.add_argument("--combined-dir", help="Directory containing mixed results (will split 5/5)")
    
    args = parser.parse_args()

    gpt5_results = []
    claude_results = []

    if args.gpt_dir:
        files = find_result_files(Path(args.gpt_dir))
        gpt5_results = [parse_result_file(f) for f in files]
    
    if args.claude_dir:
        files = find_result_files(Path(args.claude_dir))
        claude_results = [parse_result_file(f) for f in files]

    if args.combined_dir and not (gpt5_results or claude_results):
        files = find_result_files(Path(args.combined_dir))
        # Sort by modification time to try to preserve order if possible
        all_files = sorted(files, key=lambda x: x.stat().st_mtime)
        all_parsed = [parse_result_file(f) for f in all_files]
        
        if len(all_parsed) == 10:
            gpt5_results = all_parsed[:5]
            claude_results = all_parsed[5:]
        else:
            split = len(all_parsed) // 2
            gpt5_results = all_parsed[:split]
            claude_results = all_parsed[split:]

    if not gpt5_results and not claude_results:
        print(f"## ⚠️ Difficulty Evaluation: No Results Found", file=sys.stdout)
        print(f"No evaluation results found for task: {args.task_name}", file=sys.stdout)
        sys.exit(1)

    # Format and print
    print(format_results_for_github(gpt5_results, claude_results, args.task_name))

    # Exit with code logic
    gpt5_rate = calculate_pass_rate(gpt5_results)[2]
    claude_rate = calculate_pass_rate(claude_results)[2]
    best_rate = max(gpt5_rate, claude_rate)
    
    gpt5_broken = gpt5_results and all(r["episodes"] == 0 for r in gpt5_results)
    claude_broken = claude_results and all(r["episodes"] == 0 for r in claude_results)
    
    if gpt5_broken or claude_broken or best_rate < 20 or best_rate >= 80:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
