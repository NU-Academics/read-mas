# READ-MAS

**Requirements and Design Multi-Agent System**

READ-MAS generates software requirements specifications (SRS) and system designs from natural language queries using multi-agent AI orchestration built on Google ADK. It supports single-agent and multi-agent pipelines, RAG-augmented generation, structured output via Pydantic, and DVC-tracked experiment workflows for training, evaluation, and benchmarking.

## Installation

```bash
git clone <repository-url>
cd read-mas
uv pip install -e .
```

Set environment variables for your LLM provider as needed (e.g. `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`).

## Docker

### Build

```bash
docker compose build
```

### Main CLI

```bash
docker compose run --rm readmas run \
  --query "Design a task management app" -t single_agent -m gemini-2.5-flash
```

### Eval / benchmark CLI

**Generate samples**

```bash
docker compose run --rm readmas-eval generate-samples humaneval \
  --model openai/gpt-5-mini --agent-type single_agent
```

**Code benchmark**

```bash
docker compose run --rm readmas-eval code-benchmark \
  --model openai/gpt-5-mini --agent-type single_agent --rag true --dataset humaneval
```

All readmas-eval subcommands (train, eval, benchmark, llm-benchmark, etc.) work the same way.

### Ollama (local models)

OLLAMA_BASE_URL=http://host.docker.internal:11434 is pre-configured in docker-compose.yml. Start Ollama on your host then pass the model name directly:

```bash
docker compose run --rm readmas run \
  --query "Design a chat app" -t single_agent -m ollama_chat/gpt-oss:20b
```

## Usage

### Running the CLI

```bash
# Single agent mode
readmas run --query "Design a task management app" -t single_agent -m gemini-2.5-flash

# Multi-agent mode
readmas run --query "Design a chat app" -t read_agent -m gemini-2.5-flash --rag true
```

**Flags:**

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--query` | `-q` | Natural language query describing the software | — |
| `--agent-type` | `-t` | `single_agent` or `read_agent` (multi-agent) | `single_agent` |
| `--llm-model-name` | `-m` | LLM model name | `gemini-2.5-flash` |
| `--rag` | `-r` | Enable RAG retrieval | `false` |
| `--run-id` | `-i` | Unique run identifier | auto-generated |

Outputs are saved to `runs/{run_id}/logs/`.

### RAG Setup

When using `--rag true`, the RAG MCP server must be running first:

```bash
python -m src.rag.retriever_mcp_server
```

This starts the retrieval server on `http://127.0.0.1:8001/mcp`, which provides requirement examples via FAISS + Gemini embeddings.

## Architecture

### Single Agent (`single_agent`)

One `SingleAgent` handles both requirements and design in a single pass.

### Multi-Agent (`read_agent`)

A `SequentialAgent` pipeline with specialized agents for each phase:

```
ReadWrapperAgent
├── RequirementsWrapperAgent  (served via A2A on port 8002)
│   └── CollectorAgent → AnalyzerAgent → SpecifierAgent
└── DesignWrapperAgent        (served via A2A on port 8003)
    └── DesignerAgent → DocumenterAgent
```

`ReadWrapperAgent` communicates with each sub-pipeline via Google ADK's Agent-to-Agent (A2A) protocol. `re_agent` and `design_agent` are exposed as `RemoteA2aAgent` stubs; the actual agents run as separate A2A server processes.

#### A2A Servers

Two A2A server apps are defined in `src/orchestrator/read_wrapper.py`:

| App | Function | Port | Agent |
|-----|----------|------|-------|
| `re_a2a_app` | `_build_re_a2a_app()` | 8002 | `RequirementsWrapperAgent` |
| `design_a2a_app` | `_build_design_a2a_app()` | 8003 | `DesignWrapperAgent` |

Each app is created with `to_a2a(agent, port=..., agent_card=...)` and reads model, run mode, and RAG settings from environment variables (`READMAS_MODEL`, `READMAS_RUN_MODE`, `READMAS_RAG`). The apps and `root_agent` are lazy-loaded at module level to avoid unnecessary instantiation at import time.

To run the A2A servers before invoking the multi-agent pipeline:

```bash
# Terminal 1 — requirements A2A server
uvicorn src.orchestrator.read_wrapper:re_a2a_app --host localhost --port 8002

# Terminal 2 — design A2A server
uvicorn src.orchestrator.read_wrapper:design_a2a_app --host localhost --port 8003
```

### Key Patterns

- **AgentBase** (`src/agents/agent_base.py`): All agents extend this base class, which provides LLM model init, system prompt, run mode, and RAG config. Each subclass implements `get_agent()` returning a Google ADK `Agent`.
- **LLM routing** (`src/agents/agent_util.py`): Gemini models use native ADK support; Ollama and others are wrapped via LiteLLM.
- **RAG** (`src/rag/retriever.py`): FAISS index over requirement chunks, embedded with the Gemini embedding model, returns top-5 results filtered by distance. Registered as a tool on agents when `--rag` is enabled.
- **Structured output**: Collector, Analyzer, and Designer agents produce Pydantic models; downstream agents consume these.

## DVC Experiments

All training, evaluation, and benchmarking stages are defined in `dvc.yaml` and parameterized via `params.yaml`. Run them as DVC experiments:

### Data Setup

Data files (golden test cases, knowledge bases, etc.) are tracked with DVC and must be pulled before running any experiments:

```bash
dvc pull
```

### Training (prompt optimization)

```bash
dvc exp run -S train.agent_name=single_agent -S train.model=gemini-2.5-flash -S train.rag=true -S train.no_opt=true --name my-train-exp train
```

### Evaluation

```bash
dvc exp run -S eval.agent_name=single_agent -S eval.model=gemini-2.5-flash -S eval.rag=true --name my-eval-exp eval
```

### Benchmark

```bash
dvc exp run -S benchmark.agent_name=single_agent -S benchmark.model=gemini-2.5-flash -S benchmark.rag=false --name my-bench-exp benchmark
```

### Code Benchmark (agent-based)

```bash
# 1. Generate samples, 2. sanitize, 3. run experiment
readmas-eval generate-samples humaneval -m gemini-2.5-flash -t single_agent
python -m evalplus.sanitize --samples data/samples/humaneval/<samples>.jsonl
dvc exp run -S code.agent_name=single_agent -S code.model=gemini-2.5-flash \
  -S code.dataset=humaneval -S code.samples=data/samples/humaneval/<samples>-sanitized.jsonl \
  --name my-code-exp code_benchmark
```

### LLM Benchmark (direct, no agents)

Benchmarks a raw LLM on HumanEval/MBPP without agent orchestration, using litellm-format model strings.

```bash
# 1. Generate samples directly from LLM, 2. sanitize, 3. run experiment
readmas-eval llm-generate-samples humaneval -m anthropic/claude-sonnet-4-5
python -m evalplus.sanitize --samples data/samples/humaneval/<samples>.jsonl
dvc exp run -S llm.model=anthropic/claude-sonnet-4-5 -S llm.dataset=humaneval \
  -S llm.samples=data/samples/humaneval/<samples>-sanitized.jsonl \
  --name my-llm-exp llm_code_benchmark
```

Metrics (`pass@1`, `pass@1plus`) are written to `runs/llm_benchmark_runs/metrics.json`.

### Viewing Results

```bash
# Compare experiment results
dvc exp show

# Visualize metrics
dvc plots show
```

### params.yaml Structure

```yaml
train:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: true
  no_opt: false
eval:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: true
benchmark:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: false
code:
  agent_name: single_agent
  model: gemini-2.5-flash
  rag: false
  dataset: humaneval
  samples: data/samples/humaneval/<samples_file>-sanitized.jsonl
llm:
  model: anthropic/claude-sonnet-4-5
  dataset: humaneval
  samples: data/samples/humaneval/<samples_file>-sanitized.jsonl
```

## Eval CLI

The eval CLI (`readmas-eval` or `python -m src.eval.run`) provides direct access to each stage:

```bash
# Training
readmas-eval train -t single_agent -m gemini-2.5-flash -r true -n -e

# Evaluation
readmas-eval eval -t single_agent -m gemini-2.5-flash -r true -e

# Benchmark
readmas-eval benchmark -t single_agent -m gemini-2.5-flash -r false -e

# Code benchmark (agent-based)
readmas-eval code-benchmark -t single_agent -m gemini-2.5-flash -d humaneval -s <samples_file> -e

# Generate agent samples
readmas-eval generate-samples humaneval -m gemini-2.5-flash

# LLM benchmark (no agents)
readmas-eval llm-benchmark -m anthropic/claude-sonnet-4-5 -d humaneval -s <samples_file> -e

# Generate LLM samples directly
readmas-eval llm-generate-samples humaneval -m anthropic/claude-sonnet-4-5
```

**Common flags:** `-t` agent type, `-m` model, `-r` RAG toggle, `-n` skip prompt optimization (train only), `-e` DVC experiment mode, `-i` run ID.

## Project Structure

```
read-mas/
├── src/
│   ├── agents/           # Base agent classes and utilities
│   ├── requirement/      # Requirements agents (Collector, Analyzer, Specifier)
│   ├── design/           # Design agents (Designer, Documenter)
│   ├── single/           # Single agent implementation
│   ├── orchestrator/     # Agent orchestration and session management
│   ├── rag/              # RAG retriever (FAISS + Ollama embeddings)
│   ├── eval/             # Evaluation framework
│   │   ├── eval_agents/  # Evaluation-specific agents
│   │   ├── evaluators/   # Trainer, evaluator, and benchmarkers
│   │   └── run.py        # Eval CLI entry point
│   ├── prompt_templates/ # System prompts for each agent
│   ├── tools/            # Agent tools (save_to_file, RAG)
│   ├── utils/            # Logging, constants, helpers
│   └── main.py           # Main CLI entry point
├── data/                 # Goldens, samples, and results
├── runs/                 # Execution logs and outputs
├── templates/            # SRS and design document templates
├── kb/                   # Knowledge bases for domain guidance
├── dvc.yaml              # DVC pipeline stages
├── params.yaml           # Experiment parameters
└── pyproject.toml        # Project configuration
```

## Development

```bash
# Run tests
pytest

# Format code (pyink, 2-space indent, 100 char line length)
pyink src/
```

Python >= 3.12 required.

## License

See `LICENSE` file for details.

## Contributing

This is a research project. For contributions or questions, please open an issue.
