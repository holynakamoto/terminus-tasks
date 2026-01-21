# 🚀 LLM Performance Optimization Guide (2026 Edition)

This document outlines the performance and cost-saving optimizations implemented in the `terminus-tasks` pipeline for frontier models like **GPT-5** and **Claude Sonnet 4.5**.

## 1. Prompt Caching (High Priority)
We utilize **Prompt Caching** to reduce latency and costs by up to 90% for repetitive tasks.

- **Implementation**: In `nodes.py`, we use Anthropic's `cache_control` markers on the task instruction and system prompt.
- **Why**: Since CI runs evaluate the same task multiple times, the instruction set stays constant. Caching this "prefix" makes subsequent runs significantly faster.

## 2. Completion Token Management
We aggressively control output length to reduce "time to final token" and lower costs.

- **Implementation**: Standardized `max_tokens` (now `max_completion_tokens` in 2026) to **2048** in `graph_config.py`.
- **Optimization**: This provides enough room for deep reasoning traces (Chain of Thought) while preventing the model from becoming overly verbose.

## 3. Concise Instruction Engineering
Based on reasoning-model best practices, we use high-density system prompts.

- **Implementation**: Refined `AGENT_SYSTEM_PROMPT` to remove conversational filler.
- **Instructions**:
  - "Be concise. Brief planning only."
  - "Execute precisely. Check results immediately."
  - "Stop once verified."

## 4. Massive Parallelization
Independent evaluation runs are parallelized at the workflow level.

- **Implementation**: Matrix strategy in `.github/workflows/task-validation.yml` firing 5 concurrent runs for each model.
- **Impact**: Wall-clock time reduced from ~40 mins to **~7 mins** for difficulty evaluation.

## 5. Streaming & Latency (UI/UX)
While CI is non-interactive, the `harbor` tool supports streaming for local development.

- **Implementation**: `stream=True` in individual agent nodes (where supported by the runner).

## 6. Model Selection Strategy
We prioritize the **Sonnet 4.5** variant for its superior coding/agentic performance at a 5x lower price point than Opus-class models.

---
_Optimizations implemented on 2026-01-21 to meet the <25min CI execution target._
