#!/bin/bash

# Debug version of test-oracle function
task_path="${1}"
debug_mode="${2:-false}"

echo "🔍 DEBUG: test-oracle called with path='$1', debug_mode='$debug_mode'" >&2

if [ -z "$task_path" ]; then
  if [ -f "./task.toml" ]; then
    task_path="$(pwd)"
    echo "🔍 DEBUG: No path provided, using current directory: $task_path" >&2
  else
    echo "❌ No task.toml found. Specify a path."
    exit 1
  fi
fi

# Convert to absolute path and expand tilde
task_path="${task_path/#\~/$HOME}"
task_path="$(cd "$task_path" 2>/dev/null && pwd)" || {
  echo "❌ Invalid path: $1"
  exit 1
}

echo "🔍 DEBUG: Final task_path: $task_path" >&2
echo "🔍 DEBUG: Checking if task.toml exists..." >&2
if [ -f "$task_path/task.toml" ]; then
  echo "🔍 DEBUG: task.toml found" >&2
else
  echo "🔍 DEBUG: task.toml NOT found" >&2
fi

echo "🔍 DEBUG: Checking Docker status..." >&2
if command -v docker &> /dev/null; then
  echo "🔍 DEBUG: Docker is available" >&2
  if docker info &> /dev/null; then
    echo "🔍 DEBUG: Docker daemon is running" >&2
  else
    echo "🔍 DEBUG: Docker daemon is NOT running" >&2
  fi
else
  echo "🔍 DEBUG: Docker is NOT available" >&2
fi

echo "🔍 DEBUG: Checking uv/harbor installation..." >&2
if command -v uv &> /dev/null; then
  echo "🔍 DEBUG: uv is available: $(which uv)" >&2
  echo "🔍 DEBUG: uv version: $(uv --version)" >&2
else
  echo "🔍 DEBUG: uv is NOT available" >&2
fi

echo "🧪 Testing Oracle on: $task_path"

if [ "$debug_mode" = "true" ]; then
  echo "🔍 DEBUG: Running harbor with verbose output..." >&2
  uv run harbor run --agent oracle --path "$task_path" --verbose
else
  echo "🔍 DEBUG: Running harbor normally..." >&2
  uv run harbor run --agent oracle --path "$task_path"
fi

exit_code=$?
echo "🔍 DEBUG: Harbor exited with code: $exit_code" >&2

if [ $exit_code -ne 0 ]; then
  echo "🔍 DEBUG: Checking recent Harbor logs..." >&2
  latest_job_dir="$(ls -t "$task_path/jobs" 2>/dev/null | head -1)"
  if [ -n "$latest_job_dir" ]; then
    echo "🔍 DEBUG: Latest job directory: $latest_job_dir" >&2
    local exception_file="$task_path/jobs/$latest_job_dir/arm7-triage"*/exception.txt
    for exc_file in $exception_file; do
      if [ -f "$exc_file" ]; then
        echo "🔍 DEBUG: Exception file contents:" >&2
        tail -10 "$exc_file" >&2
        break
      fi
    done
  fi
fi

exit $exit_code