# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

READ-MAS (Requirements and Design Multi-Agent System) generates software requirements specifications (SRS) and system designs from natural language queries using multi-agent AI orchestration built on Google ADK.

## Commands

```bash
# Install (editable)
uv pip install -e .

# Run the CLI
readmas run --query "Design a task management app" -t single -m ollama_chat/gpt-oss:20b
readmas run --query "Design a chat app" -t multi --rag true

# Format code (pyink, 2-space indent, 100 char line length)
pyink src/

# Run tests
pytest

# DVC pipeline (prompt optimization)
dvc repro
dvc params set eval.agent_name "collector_agent"

# Evaluation
python -m src.eval.run generate-samples humaneval --model gpt-4 --num-samples 2
python -m src.eval.run generate-goldens --model gpt-4
```

## Architecture

### Two Operational Modes

**Single Agent** (`-t single`): One `SingleAgent` handles both requirements and design in a single pass.

**Multi-Agent** (`-t multi`): A `SequentialAgent` pipeline:
```
ReadWrapperAgent
├── RequirementsWrapperAgent
│   └── CollectorAgent → AnalyzerAgent → SpecifierAgent
└── DesignWrapperAgent
    └── DesignerAgent → DocumenterAgent
```

### Key Architectural Patterns

- **All agents** extend `AgentBase` (`src/agents/agent_base.py`), which provides LLM model init, system prompt, run mode, and RAG config. Each subclass implements `get_agent()` returning a Google ADK `Agent`.
- **LLM routing** is in `src/agents/agent_util.py`: Gemini models use native ADK support; Ollama and others are wrapped via LiteLLM.
- **Orchestration** (`src/orchestrator/orchestrator.py`): Creates sessions via `SessionManager`, runs agents with retry logic (3 attempts, 60s delay), and streams ADK events.
- **RAG** (`src/rag/retriever.py`): FAISS index over requirement chunks, embedded with Ollama `nomic-embed-text:latest`, returns top-3 results. Registered as a tool on agents when `--rag true`.
- **Structured output**: Collector, Analyzer, and Designer agents produce Pydantic models (`*_models.py` files); downstream agents consume these.
- **Run modes** (`AgentRunMode`): `MAIN` (normal), `EVAL` (evaluation), `BENCHMARK` (no file output). Controls whether `save_to_file` tool is attached.

### Prompt System

System prompts live in `src/prompt_templates/` as Python string constants. Each agent has a dedicated prompt file. Templates (`templates/`) define SRS and design document structure. Knowledge bases (`kb/`) provide domain guidance.

### Evaluation & Optimization

- `src/eval/evaluators/agent_evals/eval_optimize.py`: Uses DeepEval `PromptOptimizer` to iteratively improve agent system prompts, tracked with DVCLive.
- `src/eval/evaluators/benchmark_evals/`: Code generation benchmarks via `evalplus`.
- Pipeline config: `dvc.yaml` defines stages; `params.yaml` holds eval parameters (agent name, model, RAG toggle).
- Golden test cases stored in `data/goldens/`.

### Output

Agent outputs (SRS docs, design docs, logs) are saved to `runs/{run_id}/logs/` via the `save_to_file` tool (`src/tools/save_to_file_tool.py`). ADK events are logged as JSONL.

## Code Style

- Formatter: **Pyink** (Black-based), 2-space indentation, 100-char line length
- Python >= 3.11
- Logging: `loguru` via `src/utils/logger.py`
