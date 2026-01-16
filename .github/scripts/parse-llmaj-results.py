#!/usr/bin/env python3
"""
Parse LLMaJ check results and display them in a human-readable format.
Handles harbor's actual task quality check output format.
"""
import json
import sys
from pathlib import Path


def parse_llmaj_results(llmaj_json_path: str) -> dict:
    """Parse LLMaJ JSON output and extract key metrics."""
    try:
        with open(llmaj_json_path, 'r') as f:
            data = json.load(f)

        results = {
            "overall_status": "unknown",
            "passed_count": 0,
            "failed_count": 0,
            "checks": []
        }

        # Harbor's format has a 'checks' array with objects containing:
        # - check: name of the check
        # - outcome: "pass" or "fail"
        # - explanation: detailed explanation
        if isinstance(data, dict) and "checks" in data:
            for check in data["checks"]:
                check_name = check.get("check", "Unknown Check")
                outcome = check.get("outcome", "unknown")
                explanation = check.get("explanation", "No explanation provided")

                results["checks"].append({
                    "name": check_name,
                    "outcome": outcome,
                    "explanation": explanation
                })

                if outcome == "pass":
                    results["passed_count"] += 1
                elif outcome == "fail":
                    results["failed_count"] += 1

            # Determine overall status
            if results["failed_count"] == 0:
                results["overall_status"] = "passed"
            else:
                results["overall_status"] = "failed"

        # Fallback: if no checks found, try other formats
        elif isinstance(data, dict):
            if "status" in data:
                results["overall_status"] = data["status"]
            elif "passed" in data:
                results["overall_status"] = "passed" if data["passed"] else "failed"

        return results

    except FileNotFoundError:
        return {
            "overall_status": "error",
            "passed_count": 0,
            "failed_count": 0,
            "checks": [{
                "name": "File Error",
                "outcome": "error",
                "explanation": f"LLMaJ output file not found: {llmaj_json_path}"
            }]
        }
    except json.JSONDecodeError as e:
        return {
            "overall_status": "error",
            "passed_count": 0,
            "failed_count": 0,
            "checks": [{
                "name": "Parse Error",
                "outcome": "error",
                "explanation": f"Failed to parse LLMaJ JSON: {e}"
            }]
        }
    except Exception as e:
        return {
            "overall_status": "error",
            "passed_count": 0,
            "failed_count": 0,
            "checks": [{
                "name": "Unexpected Error",
                "outcome": "error",
                "explanation": f"Unexpected error: {e}"
            }]
        }


def format_results_for_github(results: dict, task_name: str = "") -> str:
    """Format LLMaJ results for GitHub Actions summary."""
    output = []

    # Note: Header is now output by the workflow itself, so we skip it here

    # Overall status
    passed = results["passed_count"]
    failed = results["failed_count"]
    total = passed + failed

    if results["overall_status"] == "passed":
        output.append(f"### ✅ Overall: PASSED ({passed}/{total} checks passed)")
    elif results["overall_status"] == "failed":
        output.append(f"### ❌ Overall: FAILED ({failed}/{total} checks failed)")
    else:
        output.append(f"### ⚠️ Overall: {results['overall_status'].upper()}")

    output.append("")

    # Failed checks first (most important)
    failed_checks = [c for c in results["checks"] if c["outcome"] in ["fail", "error"]]
    if failed_checks:
        output.append("### ❌ Failed Checks")
        output.append("")
        for check in failed_checks:
            name = check["name"]
            explanation = check["explanation"]
            output.append(f"**{name}**")
            output.append(f"> {explanation}")
            output.append("")

    # Passed checks (summary)
    passed_checks = [c for c in results["checks"] if c["outcome"] == "pass"]
    if passed_checks:
        output.append(f"### ✅ Passed Checks ({len(passed_checks)})")
        output.append("")
        for check in passed_checks:
            name = check["name"]
            # Truncate long explanations for passed checks
            explanation = check["explanation"]
            if len(explanation) > 100:
                explanation = explanation[:97] + "..."
            output.append(f"- **{name}**: {explanation}")
        output.append("")

    return "\n".join(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: parse-llmaj-results.py <llmaj_json_path> [task_name]", file=sys.stderr)
        sys.exit(1)

    llmaj_json_path = sys.argv[1]
    task_name = sys.argv[2] if len(sys.argv) > 2 else ""

    # Parse results
    results = parse_llmaj_results(llmaj_json_path)

    # Format for GitHub
    formatted_output = format_results_for_github(results, task_name)

    # Print to stdout for GitHub Actions
    print(formatted_output)

    # Exit with error code if failed
    if results["overall_status"] in ["failed", "error"] or results["failed_count"] > 0:
        sys.exit(0)  # Don't fail the step, just report
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
