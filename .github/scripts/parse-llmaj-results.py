#!/usr/bin/env python3
"""
Parse LLMaJ check results and display them in a human-readable format.
"""
import json
import sys
from pathlib import Path


def parse_llmaj_results(llmaj_json_path: str) -> dict:
    """Parse LLMaJ JSON output and extract key metrics."""
    try:
        with open(llmaj_json_path, 'r') as f:
            data = json.load(f)

        # Extract relevant information from LLMaJ output
        # The exact structure depends on harbor's output format
        # This is a general parser that handles common fields

        results = {
            "overall_status": "unknown",
            "issues": [],
            "warnings": [],
            "passed_checks": [],
            "failed_checks": []
        }

        # Handle different possible LLMaJ output formats
        if isinstance(data, dict):
            # Check for common status fields
            if "status" in data:
                results["overall_status"] = data["status"]
            elif "passed" in data:
                results["overall_status"] = "passed" if data["passed"] else "failed"

            # Extract issues/warnings
            if "issues" in data:
                results["issues"] = data["issues"]
            if "warnings" in data:
                results["warnings"] = data["warnings"]

            # Extract check results
            if "checks" in data:
                for check in data["checks"]:
                    if check.get("passed", False):
                        results["passed_checks"].append(check)
                    else:
                        results["failed_checks"].append(check)

        return results

    except FileNotFoundError:
        return {
            "overall_status": "error",
            "issues": ["LLMaJ output file not found"],
            "warnings": [],
            "passed_checks": [],
            "failed_checks": []
        }
    except json.JSONDecodeError as e:
        return {
            "overall_status": "error",
            "issues": [f"Failed to parse LLMaJ JSON: {e}"],
            "warnings": [],
            "passed_checks": [],
            "failed_checks": []
        }


def format_results_for_github(results: dict) -> str:
    """Format LLMaJ results for GitHub Actions summary."""
    output = []

    # Overall status
    if results["overall_status"] == "passed":
        output.append("✅ **LLMaJ Check: PASSED**")
    elif results["overall_status"] == "failed":
        output.append("❌ **LLMaJ Check: FAILED**")
    else:
        output.append("⚠️ **LLMaJ Check: " + results["overall_status"].upper() + "**")

    output.append("")

    # Failed checks (most important)
    if results["failed_checks"]:
        output.append("### ❌ Failed Checks")
        for check in results["failed_checks"]:
            name = check.get("name", "Unknown check")
            message = check.get("message", "No details available")
            output.append(f"- **{name}**: {message}")
        output.append("")

    # Issues
    if results["issues"]:
        output.append("### 🔴 Issues")
        for issue in results["issues"]:
            output.append(f"- {issue}")
        output.append("")

    # Warnings
    if results["warnings"]:
        output.append("### ⚠️ Warnings")
        for warning in results["warnings"]:
            output.append(f"- {warning}")
        output.append("")

    # Passed checks (for completeness)
    if results["passed_checks"]:
        output.append(f"### ✅ Passed Checks ({len(results['passed_checks'])})")
        for check in results["passed_checks"]:
            name = check.get("name", "Unknown check")
            output.append(f"- {name}")
        output.append("")

    return "\n".join(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: parse-llmaj-results.py <llmaj_json_path>", file=sys.stderr)
        sys.exit(1)

    llmaj_json_path = sys.argv[1]

    # Parse results
    results = parse_llmaj_results(llmaj_json_path)

    # Format for GitHub
    formatted_output = format_results_for_github(results)

    # Print to stdout for GitHub Actions
    print(formatted_output)

    # Exit with error code if failed
    if results["overall_status"] == "failed" or results["issues"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
